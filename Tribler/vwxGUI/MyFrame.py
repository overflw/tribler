# -*- coding: iso-8859-1 -*-
# Don't modify comment 

import wx
from bgPanel import *
from tribler_topButton import *
from standardOverview import *
from standardDetails import *
[ID_MENU_444,ID_MENU_446] = 444,446
#[inc]add your include files here

#[inc]end your include

class MyFrame(wx.Frame):
    def __init__(self,parent,id = -1,title='',pos = wx.Point(1,1),size = wx.Size(1024,768),style = wx.DEFAULT_FRAME_STYLE,name = 'frame'):
        pre=wx.PreFrame()
        self.OnPreCreate()
        pre.Create(parent,id,title,pos,size,style,name)
        self.PostCreate(pre)
        self.initBefore()
        self.VwXinit()
        self.initAfter()

    def __del__(self):
        self.Ddel()
        return


    def VwXinit(self):
        self.fileImgBuf=[None] * 8
        self.fileImgBuf[0] = wx.Bitmap("images/topbg1.png",wx.BITMAP_TYPE_PNG)
        self.fileImgBuf[1] = wx.Bitmap("images/tribler_topbutton0.png",wx.BITMAP_TYPE_PNG)
        self.fileImgBuf[2] = wx.Bitmap("images/tribler_topbutton1.png",wx.BITMAP_TYPE_PNG)
        self.fileImgBuf[3] = wx.Bitmap("images/tribler_topbutton2.png",wx.BITMAP_TYPE_PNG)
        self.fileImgBuf[4] = wx.Bitmap("images/tribler_topbutton3.png",wx.BITMAP_TYPE_PNG)
        self.fileImgBuf[5] = wx.Bitmap("images/tribler_topbutton5.png",wx.BITMAP_TYPE_PNG)
        self.fileImgBuf[6] = wx.Bitmap("images/tribler_topbutton4.png",wx.BITMAP_TYPE_PNG)
        self.fileImgBuf[7] = wx.Bitmap("images/topbg2.png",wx.BITMAP_TYPE_PNG)
        self.topBG1Img0=self.fileImgBuf[0];
        self.mainButtonFilesImg0=self.fileImgBuf[1];
        self.mainButtonPersonsImg0=self.fileImgBuf[2];
        self.mainButtonProfileImg0=self.fileImgBuf[3];
        self.mainButtonLibraryImg0=self.fileImgBuf[4];
        self.mainButtonRssImg0=self.fileImgBuf[5];
        self.mainButtonFriendsImg0=self.fileImgBuf[6];
        self.topBG2_greyImg0=self.fileImgBuf[7];
        self.SetToolTipString('d')
        self.Show(False)
        self.SetBackgroundColour(wx.Colour(212,208,200))
        self.fdfs= wx.MenuBar()
        self.menu443 = wx.Menu()
        self.fdfs.Append(self.menu443,"File")
        itemmenu = wx.MenuItem(self.menu443,ID_MENU_444,"Exit","",0)
        self.menu443.AppendItem(itemmenu)
        self.menu445 = wx.Menu()
        self.fdfs.Append(self.menu445,"Options")
        itemmenu = wx.MenuItem(self.menu445,ID_MENU_446,"Options","",0)
        self.menu445.AppendItem(itemmenu)
        self.SetMenuBar(self.fdfs)
        self.level0 = wx.ScrolledWindow(self,-1,wx.Point(0,0),wx.Size(1024,768),wx.VSCROLL|wx.HSCROLL|wx.CLIP_CHILDREN)
        self.level0.SetBackgroundColour(wx.Colour(102,102,102))
        self.topBG1 = bgPanel(self.level0, -1, wx.Point(0,0), wx.Size(449,89))
        self.topBG1.SetBackgroundColour(wx.SystemSettings.GetColour(wx.SYS_COLOUR_BACKGROUND))
        self.topBG1.Bind(wx.EVT_ERASE_BACKGROUND,self.VwXtopBG1_VwXEvOnEraseBackground)
        self.backButton = tribler_topButton(self.topBG1, -1, wx.Point(0,59), wx.Size(25,29))
        self.mainButtonFiles = tribler_topButton(self.topBG1, -1, wx.Point(29,5), wx.Size(60,72))
        # bla bla
        
        #fdsfdsf

        self.mainButtonFiles.Bind(wx.EVT_ERASE_BACKGROUND,self.VwXmainButtonFiles_VwXEvOnEraseBackground)
        self.mainButtonPersons = tribler_topButton(self.topBG1, -1, wx.Point(89,5), wx.Size(60,72))
        self.mainButtonPersons.Bind(wx.EVT_ERASE_BACKGROUND,self.VwXmainButtonPersons_VwXEvOnEraseBackground)
        self.mainButtonProfile = tribler_topButton(self.topBG1, -1, wx.Point(191,5), wx.Size(60,72))
        self.mainButtonProfile.Bind(wx.EVT_ERASE_BACKGROUND,self.VwXmainButtonProfile_VwXEvOnEraseBackground)
        self.mainButtonLibrary = tribler_topButton(self.topBG1, -1, wx.Point(251,5), wx.Size(60,72))
        self.mainButtonLibrary.Bind(wx.EVT_ERASE_BACKGROUND,self.VwXmainButtonLibrary_VwXEvOnEraseBackground)
        self.mainButtonRss = tribler_topButton(self.topBG1, -1, wx.Point(311,5), wx.Size(60,72))
        self.mainButtonRss.Bind(wx.EVT_ERASE_BACKGROUND,self.VwXmainButtonRss_VwXEvOnEraseBackground)
        self.mainButtonFriends = tribler_topButton(self.topBG1, -1, wx.Point(371,5), wx.Size(60,72))
        self.mainButtonFriends.Bind(wx.EVT_ERASE_BACKGROUND,self.VwXmainButtonFriends_VwXEvOnEraseBackground)
        self.topBG2_grey = bgPanel(self.level0, -1, wx.Point(449,0), wx.Size(128,89))
        self.topBG2_grey.Bind(wx.EVT_ERASE_BACKGROUND,self.VwXtopBG2_grey_VwXEvOnEraseBackground)
        self.topBG3 = bgPanel(self.level0, -1, wx.Point(577,0), wx.Size(287,89))
        self.topBG3.SetBackgroundColour(wx.Colour(216,216,191))
        self.tx220cCCC = wx.TextCtrl(self.topBG3,-1,"",wx.Point(82,3),wx.Size(151,22))
        self.tx220cCCC.SetLabel('search a file')
        self.tx220cCCC.SetFont(wx.Font(10,74,90,90,0,"Verdana"))
        self.bt257cC = wx.Button(self.topBG3,-1,"",wx.Point(77,35),wx.Size(65,20))
        self.bt257cC.SetLabel("files")
        self.bt257cC.SetFont(wx.Font(8,74,90,90,0,"Verdana"))
        self.bt258cC = wx.Button(self.topBG3,-1,"",wx.Point(146,35),wx.Size(75,20))
        self.bt258cC.SetLabel("persons")
        self.bt258cC.SetFont(wx.Font(8,74,90,90,0,"Verdana"))
        self.standardOverview = standardOverview(self.level0,-1,wx.Point(9,98),wx.Size(531,641))
        self.standardDetails = standardDetails(self.level0,-1,wxDefaultPosition,wxDefaultSize)
        self.standardDetails.SetDimensions(704,98,300,222)
        self.sz102sC = wx.BoxSizer(wx.VERTICAL)
        self.sizerTopMenu = wx.BoxSizer(wx.HORIZONTAL)
        self.sz11sCCCCCC = wx.BoxSizer(wx.HORIZONTAL)
        self.sz135s = wx.BoxSizer(wx.VERTICAL)
        self.sz164sC = wx.BoxSizer(wx.HORIZONTAL)
        self.sz213s = wx.BoxSizer(wx.VERTICAL)
        self.vertical1 = wx.BoxSizer(wx.VERTICAL)
        self.horizontal2 = wx.BoxSizer(wx.HORIZONTAL)
        self.horizontalC = wx.BoxSizer(wx.HORIZONTAL)
        self.horizontal2C = wx.BoxSizer(wx.HORIZONTAL)
        self.sz102sC.Add(self.sizerTopMenu,0,wx.EXPAND|wx.FIXED_MINSIZE,3)
        self.sz102sC.Add(self.sz11sCCCCCC,1,wx.BOTTOM|wx.EXPAND|wx.FIXED_MINSIZE,4)
        self.sizerTopMenu.Add(self.topBG1,0,wx.FIXED_MINSIZE,3)
        self.sizerTopMenu.Add(self.topBG2_grey,1,wx.EXPAND,3)
        self.sizerTopMenu.Add(self.topBG3,0,wx.EXPAND|wx.FIXED_MINSIZE,3)
        self.sz11sCCCCCC.Add(self.standardOverview,1,wx.TOP|wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.EXPAND|wx.FIXED_MINSIZE,9)
        self.sz11sCCCCCC.SetItemMinSize(self.standardOverview,603,10)
        self.sz11sCCCCCC.Add(self.sz135s,0,wx.TOP|wx.LEFT|wx.EXPAND|wx.FIXED_MINSIZE,9)
        self.sz11sCCCCCC.Add([20,675],0,wx.EXPAND|wx.FIXED_MINSIZE,3)
        self.sz135s.Add(self.standardDetails,1,wx.EXPAND|wx.FIXED_MINSIZE,9)
        self.sz164sC.Add(self.sz213s,0,wx.FIXED_MINSIZE,3)
        self.sz164sC.Add(self.mainButtonFiles,0,wx.TOP|wx.BOTTOM|wx.FIXED_MINSIZE,5)
        self.sz164sC.Add(self.mainButtonPersons,0,wx.TOP|wx.BOTTOM|wx.FIXED_MINSIZE,5)
        self.sz164sC.Add([36,72],0,wx.TOP|wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.FIXED_MINSIZE,3)
        self.sz164sC.Add(self.mainButtonProfile,0,wx.TOP|wx.BOTTOM|wx.FIXED_MINSIZE,5)
        self.sz164sC.Add(self.mainButtonLibrary,0,wx.TOP|wx.BOTTOM|wx.FIXED_MINSIZE,5)
        self.sz164sC.Add(self.mainButtonRss,0,wx.TOP|wx.BOTTOM|wx.FIXED_MINSIZE,5)
        self.sz164sC.Add(self.mainButtonFriends,0,wx.TOP|wx.BOTTOM|wx.FIXED_MINSIZE,5)
        self.sz213s.Add([29,59],0,wx.FIXED_MINSIZE,3)
        self.sz213s.Add(self.backButton,0,wx.FIXED_MINSIZE,3)
        self.vertical1.Add(self.horizontalC,0,wx.TOP|wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.FIXED_MINSIZE,3)
        self.vertical1.Add(self.horizontal2C,0,wx.TOP|wx.LEFT|wx.BOTTOM|wx.RIGHT|wx.FIXED_MINSIZE,3)
        self.vertical1.Add(self.horizontal2,0,wx.FIXED_MINSIZE,3)
        self.vertical1.Add([10,21],1,wx.FIXED_MINSIZE,3)
        self.horizontal2.Add([287,10],0,wx.FIXED_MINSIZE,3)
        self.horizontalC.Add([70,10],0,wx.FIXED_MINSIZE,3)
        self.horizontalC.Add(self.tx220cCCC,0,wx.TOP|wx.LEFT|wx.FIXED_MINSIZE,4)
        self.horizontalC.Add([10,10],1,wx.FIXED_MINSIZE,3)
        self.horizontal2C.Add([70,10],0,wx.FIXED_MINSIZE,3)
        self.horizontal2C.Add(self.bt257cC,0,wx.LEFT|wx.FIXED_MINSIZE,4)
        self.horizontal2C.Add(self.bt258cC,0,wx.LEFT|wx.FIXED_MINSIZE,6)
        self.horizontal2C.Add([10,10],1,wx.FIXED_MINSIZE,3)
        self.level0.SetSizer(self.sz102sC);self.level0.SetAutoLayout(1);self.level0.Layout();
        self.topBG1.SetSizer(self.sz164sC);self.topBG1.SetAutoLayout(1);self.topBG1.Layout();
        self.topBG3.SetSizer(self.vertical1);self.topBG3.SetAutoLayout(1);self.topBG3.Layout();
        self.Refresh()
        self.level0.SetScrollbars(1,1,1,1)
        self.level0.FitInside()
        return
    def VwXDrawBackImg(self,event,win,bitMap,opz):
        if (event.GetDC()):
            dc=event.GetDC()
        else: dc = wx.ClientDC(win)
        dc.SetBackground(wx.Brush(win.GetBackgroundColour(),wx.SOLID))
        dc.Clear()
        if (opz==0):
            dc.DrawBitmap(bitMap,0, 0, 0)
        if (opz==1):
            rec=wx.Rect()
            rec=win.GetClientRect()
            rec.SetLeft((rec.GetWidth()-bitMap.GetWidth())   / 2)
            rec.SetTop ((rec.GetHeight()-bitMap.GetHeight()) / 2)
            dc.DrawBitmap(bitMap,rec.GetLeft(),rec.GetTop(),0)
        if (opz==2):
            rec=wx.Rect()
            rec=win.GetClientRect()
            for y in range(0,rec.GetHeight(),bitMap.GetHeight()):
                for x in range(0,rec.GetWidth(),bitMap.GetWidth()):
                    dc.DrawBitmap(bitMap,x,y,0)

    def VwXDelComp(self):
        return
    def VwXtopBG1_VwXEvOnEraseBackground(self,event):
        self.VwXDrawBackImg(event,self.topBG1,self.topBG1Img0,0)
        self.topBG1_VwXEvOnEraseBackground(event)
        event.Skip(False)

        return
    def VwXmainButtonFiles_VwXEvOnEraseBackground(self,event):
        self.VwXDrawBackImg(event,self.mainButtonFiles,self.mainButtonFilesImg0,0)
        self.mainButtonFiles_VwXEvOnEraseBackground(event)
        event.Skip(False)

        return
    def VwXmainButtonPersons_VwXEvOnEraseBackground(self,event):
        self.VwXDrawBackImg(event,self.mainButtonPersons,self.mainButtonPersonsImg0,0)
        self.mainButtonPersons_VwXEvOnEraseBackground(event)
        event.Skip(False)

        return
    def VwXmainButtonProfile_VwXEvOnEraseBackground(self,event):
        self.VwXDrawBackImg(event,self.mainButtonProfile,self.mainButtonProfileImg0,0)
        self.mainButtonProfile_VwXEvOnEraseBackground(event)
        event.Skip(False)

        return
    def VwXmainButtonLibrary_VwXEvOnEraseBackground(self,event):
        self.VwXDrawBackImg(event,self.mainButtonLibrary,self.mainButtonLibraryImg0,0)
        self.mainButtonLibrary_VwXEvOnEraseBackground(event)
        event.Skip(False)

        return
    def VwXmainButtonRss_VwXEvOnEraseBackground(self,event):
        self.VwXDrawBackImg(event,self.mainButtonRss,self.mainButtonRssImg0,0)
        self.mainButtonRss_VwXEvOnEraseBackground(event)
        event.Skip(False)

        return
    def VwXmainButtonFriends_VwXEvOnEraseBackground(self,event):
        self.VwXDrawBackImg(event,self.mainButtonFriends,self.mainButtonFriendsImg0,0)
        self.mainButtonFriends_VwXEvOnEraseBackground(event)
        event.Skip(False)

        return
    def VwXtopBG2_grey_VwXEvOnEraseBackground(self,event):
        self.VwXDrawBackImg(event,self.topBG2_grey,self.topBG2_greyImg0,2)
        self.topBG2_grey_VwXEvOnEraseBackground(event)
        event.Skip(False)

        return

#[win]add your code here

    def topBG1_VwXEvOnEraseBackground(self,event): #init function
        #[5a8]Code event VwX...Don't modify[5a8]#
        #add your code here
        event.Skip()

        return #end function

    def mainButtonRss_VwXEvOnEraseBackground(self,event): #init function
        #[5b1]Code event VwX...Don't modify[5b1]#
        #add your code here
        event.Skip()

        return #end function


    def mainButtonFriends_VwXEvOnEraseBackground(self,event): #init function
        #[5b2]Code event VwX...Don't modify[5b2]#
        #add your code here
        event.Skip()

        return #end function



    def topBG2_grey_VwXEvOnEraseBackground(self,event): #init function
        #[16b]Code event VwX...Don't modify[16b]#
        #add your code here
        event.Skip()

        return #end function





    def topBG3_VwXEvOnEraseBackground(self,event): #init function
        #[ 58]Code event VwX...Don't modify[ 58]#
        #add your code here
        event.Skip()

        return #end function

    def topBg1_VwXEvOnEraseBackground(self,event): #init function
        #[ 53]Code event VwX...Don't modify[ 53]#
        #add your code here
        event.Skip()

        return #end function


    def mainButtonPersons_VwXEvOnEraseBackground(self,event): #init function
        #[61b]Code event VwX...Don't modify[61b]#
        #add your code here
        event.Skip()

        return #end function


    def mainButtonLibrary_VwXEvOnEraseBackground(self,event): #init function
        #[141]Code event VwX...Don't modify[141]#
        #add your code here
        event.Skip()

        return #end function

    def mainButtonProfile_VwXEvOnEraseBackground(self,event): #init function
        #[140]Code event VwX...Don't modify[140]#
        #add your code here
        event.Skip()

        return #end function

    def mainButtonFiles_VwXEvOnEraseBackground(self,event): #init function
        #[13f]Code event VwX...Don't modify[13f]#
        #add your code here
        event.Skip()

        return #end function


            




    def jelle(self, i):
        print i
        
    def OnPreCreate(self):
        #add your code here
        self.utility = None
        self.jelle(0)
        return

    def initBefore(self):
        #add your code here

        return

    def initAfter(self):
        #add your code here
        self.Centre() 
        self.Show()
        return

    def Ddel(self): #init function
        #[ f9]Code VwX...Don't modify[ f9]#
        #add your code here

        return #end function

#[win]end your code
