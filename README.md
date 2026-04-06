# rocky-
设计自己的桌宠
#直接下载版：
链接：https://pan.quark.cn/s/dbf61051830c
提取码：drcU

#自定义版：
1.准备环境
  安装 Python （随便选择版本，如果之前有就不用装）
  安装时勾选 “Add Python to PATH”

2.安装依赖
 在项目目录打开命令行（地址栏输入 cmd 回车），执行：
py -3.11 -m venv .venv（3.11根据你的python版本更换）
.\.venv\Scripts\activate
pip install -U pip
pip install PySide6 pyinstaller

3.准备素材(assets文件夹）
  app.ico
  day.gif
  evening.gif
  morning.gif
  night.gif
       *以上GIF会在不同时间切换，如果不需要切换可以只准备一个GIF,并修改对应代码
  myfont.ttf
      *如果用系统字体也可以不加字体文件
  任意名称.wav
      *音频素材：如果添加必须在assets文件夹里新建sfx文件夹，然后在里面放音频文件

4.打包：文件链接链接：https://pan.quark.cn/s/014af2006f19
  打包操作：1.确认文件：在你的项目目录里，创建如下结构：
                       main.py（主程序）
                       /assets（素材目录）
                            app.ico（托盘/应用图标，.ico）
                            .gif文件
                            /sfx
                               .wav
           2. 当前页面右键 “在终端中打开”
           3.依次输入：
             Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
              .\.venv\Scripts\Activate.ps1
              pyinstaller --noconfirm --onefile --windowed --add-data "assets;assets" --icon assets/app.ico main.py
           4.打包好的exe文件在dist文件夹里。
                            
