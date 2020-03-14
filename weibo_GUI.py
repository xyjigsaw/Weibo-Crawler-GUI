import wx
import urllib.request
import json
import requests
import os
from threading import *
from wx.lib.pubsub import pub
import webbrowser
import ssl

ssl._create_default_https_context = ssl._create_unverified_context

# 6012503895

ID_START = wx.NewId()
ID_STOP = wx.NewId()
EVT_RESULT_ID = wx.NewId()

path = ""
id = ''
proxy_addr = "119.101.114.49:9999"
pic_num = 0
weibo_name = ""

def use_proxy(url,proxy_addr):
    req = urllib.request.Request(url)
    req.add_header("User-Agent", "Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/49.0.2623.221 Safari/537.36 SE 2.X MetaSr 1.0")
    proxy = urllib.request.ProxyHandler({'http':proxy_addr})
    opener = urllib.request.build_opener(proxy, urllib.request.HTTPHandler)
    urllib.request.install_opener(opener)
    data = urllib.request.urlopen(req).read().decode('utf-8','ignore')
    return data


def get_containerid(url):
    data=use_proxy(url,proxy_addr)
    content=json.loads(data).get('data')
    for data in content.get('tabsInfo').get('tabs'):
        if(data.get('tab_type')=='weibo'):
            containerid=data.get('containerid')
    return containerid


def EVT_RESULT(win, func):
    win.Connect(-1, -1, EVT_RESULT_ID, func)


class WorkerThread(Thread):
    """Worker Thread Class."""
    def __init__(self, notify_window):
        """Init Worker Thread Class."""
        Thread.__init__(self)
        self._notify_window = notify_window
        self._want_abort = 0
        self.start()

    def run(self):
        global path
        global id
        global proxy_addr
        global pic_num
        global weibo_name
        try:
            os.mkdir(path + '/'+weibo_name)
        except:
            pass
        path = path + '/' +weibo_name + '/'
        file = path + weibo_name + ".txt"
        url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value=' + id
        data = use_proxy(url, proxy_addr)
        content = json.loads(data).get('data')
        profile_image_url = content.get('userInfo').get('profile_image_url')
        description = content.get('userInfo').get('description')
        profile_url = content.get('userInfo').get('profile_url')
        verified = content.get('userInfo').get('verified')
        guanzhu = content.get('userInfo').get('follow_count')
        name = content.get('userInfo').get('screen_name')
        fensi = content.get('userInfo').get('followers_count')
        gender = content.get('userInfo').get('gender')
        urank = content.get('userInfo').get('urank')
        user_info = "微博昵称：" + name + "\n" + "微博主页地址：" + profile_url + "\n" + "微博头像地址：" + profile_image_url + "\n" + "是否认证：" + str(
                verified) + "\n" + "微博说明：" + description + "\n" + "关注人数：" + str(guanzhu) + "\n" + "粉丝数：" + str(
                fensi) + "\n" + "性别：" + gender + "\n" + "微博等级：" + str(urank) + "\n"
        wx.CallAfter(pub.sendMessage, "info", msg=user_info)
        global pic_num
        i = 1
        while True:
            url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value=' + id
            weibo_url = 'https://m.weibo.cn/api/container/getIndex?type=uid&value=' + id + '&containerid=' + get_containerid(
                url) + '&page=' + str(i)
            try:
                data = use_proxy(weibo_url, proxy_addr)
                content = json.loads(data).get('data')
                cards = content.get('cards')
                wx.CallAfter(pub.sendMessage, "num", msg=len(cards))
                if self._want_abort:
                    return
                if len(cards) > 0:
                    for j in range(len(cards)):
                        wx.CallAfter(pub.sendMessage, "temp_num", msg=str(j))
                        status = "正在爬取第" + str(i) + "页，第" + str(j) + "条微博~"
                        wx.CallAfter(pub.sendMessage, "status", msg=status)
                        card_type = cards[j].get('card_type')
                        if card_type == 9:
                            mblog = cards[j].get('mblog')
                            attitudes_count = mblog.get('attitudes_count')
                            comments_count = mblog.get('comments_count')
                            created_at = mblog.get('created_at')

                            reposts_count = mblog.get('reposts_count')
                            scheme = cards[j].get('scheme')
                            text = mblog.get('text')
                            if mblog.get('pics') != None:
                                pic_archive = mblog.get('pics')
                                for _ in range(len(pic_archive)):
                                    pic_num += 1
                                    # print(pic_archive[_]['large']['url'])
                                    print(text)
                                    imgurl = pic_archive[_]['large']['url']
                                    img = requests.get(imgurl)
                                    f = open(path + str(pic_num) + str(imgurl[-4:]), 'ab')  # 存储图片，多媒体文件需要参数b（二进制文件）
                                    f.write(img.content)  # 多媒体存储content
                                    f.close()

                            with open(file, 'a', encoding='utf-8') as fh:
                                fh.write("----第" + str(i) + "页，第" + str(j) + "条微博----" + "\n")
                                fh.write("微博地址：" + str(scheme) + "\n" + "发布时间：" + str(
                                    created_at) + "\n" + "微博内容：" + text + "\n" + "点赞数：" + str(
                                    attitudes_count) + "\n" + "评论数：" + str(comments_count) + "\n" + "转发数：" + str(
                                    reposts_count) + "\n")
                            if self._want_abort:
                                return
                    i += 1
                else:
                    break
            except Exception as e:
                wx.CallAfter(pub.sendMessage, "status", msg='出现问题：'+str(e))
                if self._want_abort:
                    return
                pass

    def abort(self):
        """abort worker thread."""
        self._want_abort = 1


class InfoPanel(wx.Frame):
    def __init__(self, parent, id):
        wx.Frame.__init__(self, parent, id, "微博Spider",  pos=(0, 0), size=(650, 390))
        panel = wx.Panel(self, -1)
        self.text = wx.TextCtrl(panel, wx.ID_ANY, pos=(90, 5), size=(150, 25))
        self.info_text = wx.TextCtrl(panel, wx.ID_ANY, pos=(2, 65), size=(640, 195), style=wx.TE_MULTILINE)
        self.status_text = wx.TextCtrl(panel, wx.ID_ANY, pos=(60, 265), size=(240, 28))
        menubar = wx.MenuBar()  # 生成菜单栏
        filemenu = wx.Menu()  # 生成一个菜单
        qmi = wx.MenuItem(filemenu, wx.ID_EXIT, "代理设置")  # 生成一个菜单项
        self.Bind(wx.EVT_MENU, self.set_proxy)
        filemenu.Append(qmi)
        menubar.Append(filemenu, "&高级")  # 把菜单加入到菜单栏中
        aboutmenu = wx.Menu()
        about = wx.MenuItem(aboutmenu, wx.ID_ABOUT, "关于")  # 生成一个菜单项
        self.Bind(wx.EVT_MENU, self.AboutDialog, id=wx.ID_ABOUT)
        web = wx.MenuItem(aboutmenu, wx.ID_INFO, "开发者网站")  # 生成一个菜单项
        self.Bind(wx.EVT_MENU, self.web, id=wx.ID_INFO)
        aboutmenu.Append(about)
        aboutmenu.Append(web)
        menubar.Append(aboutmenu, "&关于")  # 把菜单加入到菜单栏中
        self.SetMenuBar(menubar)  # 把菜单栏加入到Frame框架中
        wx.StaticText(panel, -1, 'ID:', pos=(35, 8))
        wx.StaticText(panel, -1, '——————————————————微博信息列表——————————————————', pos=(35, 40))
        wx.StaticText(panel, -1, '当前进度', pos=(3, 270))
        button = wx.Button(panel, wx.ID_ANY, pos=(10, 300), size=(200, 50), label='运行')
        button.Bind(wx.EVT_BUTTON, self.running)
        button2 = wx.Button(panel, wx.ID_ANY, pos=(220, 300), size=(200, 50), label='停止')
        button2.Bind(wx.EVT_BUTTON, self.stop_running)
        button3 = wx.Button(panel, wx.ID_ANY, pos=(430, 300), size=(200, 50), label='停止并清除')
        button3.Bind(wx.EVT_BUTTON, self.clear_all)
        button4 = wx.Button(panel, wx.ID_ANY, pos=(440, 8), size=(130, 30), label='复制到剪切板')
        button4.Bind(wx.EVT_BUTTON, self.OnCopy)
        self.SetTransparent(220)
        self.bar = wx.Gauge(panel, wx.ID_ANY, pos=(310, 265), size=(330, 28))
        pub.subscribe(self.set_info, "info")
        pub.subscribe(self.set_status, "status")
        pub.subscribe(self.get_num, "num")
        pub.subscribe(self.set_temp_num, "temp_num")
        self.running_flag = 0

    def running(self, event):
        if self.running_flag == 0:
            global id
            global path
            global weibo_name
            id = self.text.GetValue()
            weibo_name = self.text.GetValue()
            if len(id) < 5:
                dlg = wx.MessageDialog(self,
                                       'ERROR 请输入正确ID！', 'ERROR!', wx.OK | wx.ICON_INFORMATION)
                dlg.ShowModal()
                dlg.Destroy()
            else:
                dlg = wx.DirDialog(self, u"选择保存的位置", style=wx.DD_DEFAULT_STYLE)
                if dlg.ShowModal() == wx.ID_OK:
                    path = dlg.GetPath()
                dlg.Destroy()
                self.running_flag = 1
                self.worker = WorkerThread(self)
        else:
            pass

    def web(self, event):
        webbrowser.open("http://www.omegaxyz.com/")

    def AboutDialog(self, event):
        dlg = wx.MessageDialog(self,
                               '更多内容请访问 OmegaXYZ.com', '关于', wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()

    def set_proxy(self, event):
        global proxy_addr
        dlg = wx.TextEntryDialog(None, "输入代理地址", '代理设置', '122.241.72.191:808')
        while True:
            try:
                if dlg.ShowModal() == wx.ID_OK:
                    proxy_addr = dlg.GetValue()
                break
            except:
                pass
        dlg.Destroy()

    def get_num(self, msg):
        self.num = int(msg)

    def set_temp_num(self, msg):
        self.bar.SetValue(int(msg)/self.num*100)

    def set_info(self, msg):
        self.info_text.AppendText(msg)

    def set_status(self, msg):
        self.status_text.Clear()
        self.status_text.AppendText(msg)

    def run_set_value(self, msg):
        self.bar.SetValue(float(msg))

    def stop_running(self, event):
        try:
            self.worker.abort()
            self.running_flag = 0
            self.bar.SetValue(0)
        except AttributeError:
            pass

    def clear_all(self, event):
        self.text.Clear()
        self.info_text.Clear()
        self.info_text.Clear()
        self.bar.SetValue(0)
        self.stop_running(self)
        self.status_text.Clear()

    def OnCopy(self, event):
        text_obj = wx.TextDataObject()
        text_obj.SetText(self.info_text.GetValue())
        if wx.TheClipboard.IsOpened() or wx.TheClipboard.Open():
            wx.TheClipboard.SetData(text_obj)
            wx.TheClipboard.Close()
        dlg = wx.MessageDialog(self,
                               '已经复制到剪切板', '复制到剪切板', wx.OK | wx.ICON_INFORMATION)
        dlg.ShowModal()
        dlg.Destroy()


class MainApp(wx.App):
    def OnInit(self):
        self.frame1 = InfoPanel(None, -1)
        self.frame1.Center()
        self.frame1.Show(True)
        self.SetTopWindow(self.frame1)
        return True

if __name__ == '__main__':
    app = MainApp(0)
    app.MainLoop()
