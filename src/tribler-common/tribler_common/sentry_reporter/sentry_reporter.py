import logging
import os
import sys
from contextlib import contextmanager
from contextvars import ContextVar
from enum import Enum, auto
from hashlib import md5
from typing import Dict, List, Optional

from faker import Faker

import sentry_sdk
from sentry_sdk.integrations.logging import LoggingIntegration, ignore_logger
from sentry_sdk.integrations.threading import ThreadingIntegration

from tribler_common.sentry_reporter.sentry_tools import (
    delete_item,
    extract_dict,
    get_first_item,
    get_value,
    parse_os_environ,
    parse_stacktrace,
)

# fmt: off

PLATFORM_DETAILS = 'platform.details'
STACKTRACE = '_stacktrace'
SYSINFO = 'sysinfo'
OS_ENVIRON = 'os.environ'
SYS_ARGV = 'sys.argv'
TAGS = 'tags'
CONTEXTS = 'contexts'
EXTRA = 'extra'
BREADCRUMBS = 'breadcrumbs'
LOGENTRY = 'logentry'
REPORTER = 'reporter'
VALUES = 'values'
RELEASE = 'release'
EXCEPTION = 'exception'


class SentryStrategy(Enum):
    """Class describes all available Sentry Strategies

    SentryReporter can work with 3 strategies:
    1. Send reports are allowed
    2. Send reports are allowed with a confirmation dialog
    3. Send reports are suppressed (but the last event will be stored)
    """

    SEND_ALLOWED = auto()
    SEND_ALLOWED_WITH_CONFIRMATION = auto()
    SEND_SUPPRESSED = auto()


@contextmanager
def this_sentry_strategy(reporter, strategy: SentryStrategy):
    saved_strategy = reporter.thread_strategy.get()
    try:
        reporter.thread_strategy.set(strategy)
        yield reporter
    finally:
        reporter.thread_strategy.set(saved_strategy)


class SentryReporter:
    """SentryReporter designed for sending reports to the Sentry server from
    a Tribler Client.
    """

    def __init__(self):
        self.scrubber = None
        self.last_event = None
        self.ignored_exceptions = [KeyboardInterrupt, SystemExit]
        # more info about how SentryReporter choose a strategy see in
        # SentryReporter.get_actual_strategy()
        self.global_strategy = SentryStrategy.SEND_ALLOWED_WITH_CONFIRMATION
        self.thread_strategy = ContextVar('context_strategy', default=None)

        self._sentry_logger_name = 'SentryReporter'
        self._logger = logging.getLogger(self._sentry_logger_name)

    def init(self, sentry_url='', release_version='', scrubber=None,
             strategy=SentryStrategy.SEND_ALLOWED_WITH_CONFIRMATION):
        """Initialization.

        This method should be called in each process that uses SentryReporter.

        Args:
            sentry_url: URL for Sentry server. If it is empty then Sentry's
                sending mechanism will not be initialized.

            scrubber: a class that will be used for scrubbing sending events.
                Only a single method should be implemented in the class:
                ```
                    def scrub_event(self, event):
                        pass
                ```
            release_version: string that represents a release version.
                See Also: https://docs.sentry.io/platforms/python/configuration/releases/
            strategy: a Sentry strategy for sending events (see class Strategy
                for more information)
        Returns:
            Sentry Guard.
        """
        self._logger.debug(f"Init: {sentry_url}")
        self.scrubber = scrubber
        self.global_strategy = strategy

        rv = sentry_sdk.init(
            sentry_url,
            release=release_version,
            # https://docs.sentry.io/platforms/python/configuration/integrations/
            integrations=[
                LoggingIntegration(
                    level=logging.INFO,  # Capture info and above as breadcrumbs
                    event_level=None,  # Send no errors as events
                ),
                ThreadingIntegration(propagate_hub=True),
            ],
            before_send=self._before_send,
            ignore_errors=[KeyboardInterrupt],
        )

        ignore_logger(self._sentry_logger_name)

        return rv

    def ignore_logger(self, logger_name: str):
        self._logger.debug(f"Ignore logger: {logger_name}")
        ignore_logger(logger_name)

    def add_breadcrumb(self, message='', category='', level='info', **kwargs):
        """Adds a breadcrumb for current Sentry client.

        It is necessary to specify a message, a category and a level to make this
        breadcrumb visible in Sentry server.

        Args:
            **kwargs: named arguments that will be added to Sentry event as well
        """
        crumb = {'message': message, 'category': category, 'level': level}

        self._logger.debug(f"Add the breadcrumb: {crumb}")

        return sentry_sdk.add_breadcrumb(crumb, **kwargs)

    def send_event(self, event: Dict = None, post_data: Dict = None, sys_info: Dict = None,
                   additional_tags: List[str] = None, retrieve_error_message_from_stacktrace=False):
        """Send the event to the Sentry server

        This method
            1. Enable Sentry's sending mechanism.
            2. Extend sending event by the information from post_data.
            3. Send the event.
            4. Disables Sentry's sending mechanism.

        Scrubbing the information will be performed in the `_before_send` method.

        During the execution of this method, all unhandled exceptions that
        will be raised, will be sent to Sentry automatically.

        Args:
            event: event to send. It should be taken from SentryReporter at
            post_data: dictionary made by the feedbackdialog.py
                previous stages of executing.
            sys_info: dictionary made by the feedbackdialog.py
            additional_tags: tags that will be added to the event

        Returns:
            Event that was sent to Sentry server
        """
        self._logger.info(f"Send: {post_data}, {event}")

        if event is None:
            return event

        post_data = post_data or dict()
        sys_info = sys_info or dict()
        additional_tags = additional_tags or dict()

        if CONTEXTS not in event:
            event[CONTEXTS] = {}

        if TAGS not in event:
            event[TAGS] = {}

        event[CONTEXTS][REPORTER] = {}

        # tags
        tags = event[TAGS]
        tags['version'] = get_value(post_data, 'version')
        tags['machine'] = get_value(post_data, 'machine')
        tags['os'] = get_value(post_data, 'os')
        tags['platform'] = get_first_item(get_value(sys_info, 'platform'))
        tags[f'{PLATFORM_DETAILS}'] = get_first_item(get_value(sys_info, PLATFORM_DETAILS))
        tags.update(additional_tags)

        # context
        context = event[CONTEXTS]
        reporter = context[REPORTER]
        version = get_value(post_data, 'version')

        context['browser'] = {'version': version, 'name': 'Tribler'}

        stacktrace_parts = parse_stacktrace(get_value(post_data, 'stack'))
        reporter[STACKTRACE] = next(stacktrace_parts, [])
        stacktrace_extra = next(stacktrace_parts, [])
        reporter[f'{STACKTRACE}_extra'] = stacktrace_extra
        reporter[f'{STACKTRACE}_context'] = next(stacktrace_parts, [])

        reporter['comments'] = get_value(post_data, 'comments')

        reporter[OS_ENVIRON] = parse_os_environ(get_value(sys_info, OS_ENVIRON))
        delete_item(sys_info, OS_ENVIRON)

        reporter['events'] = extract_dict(sys_info, r'^(event|request)')
        reporter[SYSINFO] = {key: sys_info[key] for key in sys_info if key not in reporter['events']}

        # try to retrieve an error from the stacktrace
        if retrieve_error_message_from_stacktrace and stacktrace_extra:
            exception_value = stacktrace_extra[-1].split(':', maxsplit=1)
            exception_values = event.get(EXCEPTION, {}).get(VALUES, [])
            if len(exception_value) == 2:
                exception_values.append({
                    'type': exception_value[0],
                    'value': exception_value[1]
                })

        with this_sentry_strategy(self, SentryStrategy.SEND_ALLOWED):
            sentry_sdk.capture_event(event)

        return event

    def get_confirmation(self, exception):
        """Get confirmation on sending exception to the Team.

        There are two message boxes, that will be triggered:
        1. Message box with the error_text
        2. Message box with confirmation about sending this report to the Tribler
            team.

        Args:
            exception: exception to be sent.
        """
        # Prevent importing PyQt globally in tribler-common module.
        # pylint: disable=import-outside-toplevel
        try:
            from PyQt5.QtWidgets import QApplication, QMessageBox
        except ImportError:
            self._logger.debug("PyQt5 is not available. User confirmation is not possible.")
            return False

        self._logger.debug(f"Get confirmation: {exception}")

        _ = QApplication(sys.argv)
        messagebox = QMessageBox(icon=QMessageBox.Critical, text=f'{exception}.')
        messagebox.setWindowTitle("Error")
        messagebox.exec()

        messagebox = QMessageBox(
            icon=QMessageBox.Question,
            text='Do you want to send this crash report to the Tribler team? '
                 'We anonymize all your data, who you are and what you downloaded.',
        )
        messagebox.setWindowTitle("Error")
        messagebox.setStandardButtons(QMessageBox.Yes | QMessageBox.No)

        return messagebox.exec() == QMessageBox.Yes

    def capture_exception(self, exception):
        self._logger.info(f"Capture exception: {exception}")
        sentry_sdk.capture_exception(exception)

    def event_from_exception(self, exception) -> Dict:
        """This function format the exception by passing it through sentry
        Args:
            exception: an exception that will be passed to `sentry_sdk.capture_exception(exception)`

        Returns:
            the event that has been saved in `_before_send` method
        """
        self._logger.info(f"Event from exception: {exception}")

        if not exception:
            return {}

        with this_sentry_strategy(self, SentryStrategy.SEND_SUPPRESSED):
            sentry_sdk.capture_exception(exception)
            return self.last_event

    def set_user(self, user_id):
        """Set the user to identify the event on a Sentry server

        The algorithm is the following:
        1. Calculate hash from `user_id`.
        2. Generate fake user, based on the hash.

        No real `user_id` will be used in Sentry.

        Args:
            user_id: Real user id.

        Returns:
            Generated user (dictionary: {id, username}).
        """
        # calculate hash to keep real `user_id` in secret
        user_id_hash = md5(user_id).hexdigest()

        self._logger.debug(f"Set user: {user_id_hash}")

        Faker.seed(user_id_hash)
        user_name = Faker().name()
        user = {'id': user_id_hash, 'username': user_name}

        sentry_sdk.set_user(user)
        return user

    def get_actual_strategy(self):
        """This method is used to determine actual strategy.

        Strategy can be global: self.strategy
        and local: self._context_strategy.

        Returns: the local strategy if it is defined, the global strategy otherwise
        """
        strategy = self.thread_strategy.get()
        return strategy if strategy else self.global_strategy

    @staticmethod
    def get_test_sentry_url():
        return os.environ.get('TRIBLER_TEST_SENTRY_URL', None)

    @staticmethod
    def is_in_test_mode():
        return bool(SentryReporter.get_test_sentry_url())

    def _before_send(self, event: Optional[Dict], hint: Optional[Dict]) -> Optional[Dict]:
        """The method that is called before each send. Both allowed and
        disallowed.

        The algorithm:
        1. If sending is allowed, then scrub the event and send.
        2. If sending is disallowed, then store the event in
            `self.last_event`

        Args:
            event: event that generated by Sentry
            hint: root exception (can be used in some cases)

        Returns:
            The event, prepared for sending, or `None`, if sending is suppressed.
        """
        if not event:
            return event

        # trying to get context-depending strategy first
        strategy = self.get_actual_strategy()

        self._logger.info(f"Before send strategy: {strategy}")

        exc_info = get_value(hint, 'exc_info')
        error_type = get_first_item(exc_info)

        if error_type in self.ignored_exceptions:
            self._logger.debug(f"Exception is in ignored: {hint}. Skipped.")
            return None

        if strategy == SentryStrategy.SEND_SUPPRESSED:
            self._logger.debug("Suppress sending. Storing the event.")
            self.last_event = event
            return None

        if strategy == SentryStrategy.SEND_ALLOWED_WITH_CONFIRMATION:
            self._logger.debug("Request confirmation.")
            if not self.get_confirmation(hint):
                return None

        # clean up the event
        self._logger.debug(f"Clean up the event with scrubber: {self.scrubber}")
        if self.scrubber:
            event = self.scrubber.scrub_event(event)

        return event
