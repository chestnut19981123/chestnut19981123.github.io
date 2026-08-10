---
title: Linux配置网络
categories: '技术'
tags: ['Linux', '网络']
date: 2024-06-16 16:15:39
cover: cover.png
---
## 连接网络

现在这个时代，谁离得开网络呢。连接网络的方式无非两种：有线、无线。家庭或办公室的典型布局是这样的链路：

* 调制解调器连接到ISP：调制解调器从ISP接收互联网信号。
* 调制解调器连接到路由器：通过网线，将调制解调器连接到路由器的WAN端口。
* 路由器连接到本地设备：路由器通过有线或无线方式连接到本地的计算机、手机或其他设备。

下文就按这套布局来。在 Linux 中，物理机联网靠 `nmcli` 这个命令行工具，虚拟机则直接在虚拟机软件里配置。

### 有线方式

有线就简单了：找根网线，一头插电脑，另一头插路由器的 LAN 口，然后：

1. 先确认网卡存在、驱动正常，用下面这条命令查看网络接口（有线接口的名字一般以 `eth` 或 `en` 开头）。

```bash
ip a
```

> 这里插一句：现代 Linux 推荐用 `ip` 命令，`ip a` 里的 `a` 是 `address` 的缩写，`ip a`、`ip addr`、`ip address` 三兄弟效果一样。`nmcli` 后面的单词也支持缩写，`nmcli c`、`nmcli con`、`nmcli connection` 都是一家人。

2. 网线插好后，Linux 一般会自动检测到连接并尝试获取 IP。要是它没反应，就手动请求一下。NetworkManager 环境（多数桌面发行版）用：

```bash
nmcli device connect <interface>
```

传统环境也可以用 `sudo dhclient <interface>`——不过新发行版（如 Ubuntu 23.10+、Debian 12+）默认已不带 dhclient 了。

### 无线方式

无线就全靠 `nmcli` 了，步骤稍微多一点：

1. 先确认网卡存在、驱动正常，用下面这条命令查看网络接口（无线接口的名字一般以 `wlan` 或 `wlp` 开头）。

```bash
ip a
```

2. 确认无线网卡已启用。

```bash
sudo ip link set <interface> up
```

3. 把 Wi-Fi 开关打开。

```bash
nmcli radio wifi on
```

4. 看看周围有哪些 Wi-Fi。

```bash
nmcli device wifi list
```

列表会按信号强度从强到弱排序，一眼就能看到该连哪个。

![热点列表](热点列表.png)

5. 连上去。

```bash
nmcli device wifi connect <SSID> --ask
```

> 不想交互式输密码的话，也可以把密码直接写在命令里，代价是密码会以明文形式留在终端历史中。`--ask` 会提示你交互输入，更安全，本文推荐这种方式。

### 网络模式

虚拟机的网络由虚拟机软件管理，常见模式有这几种：

* NAT模式：虚拟机通过宿主机的IP地址和端口与外部网络通信。
* 桥接模式：虚拟机直接连接到物理网络，就像一台独立的物理主机。
* 内部网络：多个虚拟机之间可以相互通信，但不能与宿主机或外部网络通信。
* 仅主机模式：虚拟机只能与宿主机通信，不能访问外部网络。

前两种能访问互联网，后两种只能在小圈子里自嗨。具体选哪种，看需求来，在虚拟机软件里配置即可。模式之间的区别和联系，可以看技术蛋老师的[视频](https://www.bilibili.com/video/BV11M4y1J7zP)：

<iframe style="width: 100%; aspect-ratio: 16/9;" src="//player.bilibili.com/player.html?bvid=BV11M4y1J7zP&poster=1&autoplay=0" frameborder="no" scrolling="no"></iframe>

在虚拟机中，可使用`ip a`命令查看网络接口。

![虚拟机查看网络地址](虚拟机查看网络地址.png)

## 静态地址

为什么要设静态 IP？因为 IP 一变，`ssh` 连接就找不到人了，虚拟机场景里尤其常见。IP 分配通常有两种方式：

* DHCP：通过DHCP服务器自动分配IP地址和配置其他网络参数。
* 静态地址：手动分配IP地址和配置其他网络参数，设备的IP地址在配置后不会改变。

下面介绍用 `nmcli` 绑定静态 IP 的方法。

### 有线连接

1. 先确认接口名（有线接口一般以 `eth` 或 `en` 开头）：

```bash
ip a
```

顺便在这一步确定当前网络，看接口信息里 `inet` 那一行。例如：

```
...
2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP group default qlen 1000
    link/ether 00:15:5d:20:74:02 brd ff:ff:ff:ff:ff:ff
    inet 192.168.31.102/24 brd 192.168.31.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::eea5:2add:2436:186%10 scope link
       valid_lft forever preferred_lft forever
...
```

这段输出告诉我们网络是 `192.168.31.0/24`：去掉网络地址 `192.168.31.0`、广播地址 `192.168.31.255` 和网关 `192.168.31.1`，剩下的 `192.168.31.2`~`192.168.31.254` 都能选，一般直接用当前的 `192.168.31.102` 就行。也可以去路由器或虚拟机配置里确认网络地址。

2. 查一下已有连接的名字（要和上一步的接口对应上）：

```bash
nmcli connection show
```

3. 然后设置 IP、网关和 DNS：

```bash
nmcli connection modify <connection> ipv4.method manual ipv4.addresses <address> ipv4.gateway <gateway> ipv4.dns <dns>
```

`connection`为连接名称，`address`为IP地址，`gateway`为网关地址，`dns`为DNS服务器地址。以上述网络为例：

* `connection`：连接名称为上一步查看到的连接名称，连接名称要与相应的接口相关联。
* `address`：IP地址建议选择`192.168.31.102/24`。该地址只要属于可选范围且不被占用即可。
* `gateway`：网关地址为`192.168.31.1`。该地址的主机部分通常为`1`，这也是访问路由器管理界面的地址。
* `dns`：DNS服务器地址建议选择`8.8.8.8`或`8.8.4.4`，选择网关地址通常也是可行的。

4. 先停用连接：

```bash
nmcli connection down <connection>
```

5. 再启用连接，之后用 `ip a` 看看地址对不对：

```bash
nmcli connection up <connection>
```

### 无线连接

无线连接和有线差不多，照着来一遍就行：

1. 确定网络接口名称，可使用以下命令查看网络接口，无线网络接口的名称一般以`wlan`或`wlp`开头。

```bash
ip a
```

2. 确定无线连接名称，可使用以下命令查看已有连接，该连接名称需要与上一步查看的接口名称相关联，其名称通常为WLAN名称。

```bash
nmcli connection show
```

3. 设置静态连接所需的IP地址、网关以及DNS等信息。

```bash
nmcli connection modify <connection> ipv4.method manual ipv4.addresses <address> ipv4.gateway <gateway> ipv4.dns <dns>
```

4. 停用连接。

```bash
nmcli connection down <connection>
```

5. 启用连接，启用后可再次使用`ip a`查看网络地址。

```bash
nmcli connection up <connection>
```

### 重置连接

设完静态 IP 后悔了？一条命令切回自动获取，再重启连接就行：

```bash
nmcli connection modify <connection> ipv4.method auto
nmcli connection down <connection> && nmcli connection up <connection>
```

不过这样操作后，`ip a` 里可能出现两个 IPv4 地址，看着有点吓人，其实问题不大。想彻底重置的话，按下面的步骤来：

1. 确定网络接口名称，可使用以下命令查看网络接口。

```bash
ip a
```

2. 确定要重置的连接名称，可使用以下命令查看已有连接，该连接名称需要与上一步查看的接口名称相关联。

```bash
nmcli connection show
```

3. 把连接删掉——就像手机里点"忘记这个网络"一样。

```bash
nmcli connection delete <connection>
```

4. 然后重新添加一个连接。

如果是有线连接，可使用下面的命令添加一个有线连接：

```bash
nmcli connection add type ethernet ifname <interface> con-name <connection>
```

如果是无线连接，可使用前文的方法添加一个无线连接：

```bash
nmcli device wifi connect <SSID> --ask
```

> 顺带一提，`nmcli connection add` 甚至能添加拨号连接——不过现在拨号大多在光猫/路由器里就设置好了，电脑早就不干这活了。

## 设置代理

不设置代理的话，访问 GitHub 这类网站经常出幺蛾子：`git clone` 超时、网页打不开。下面介绍三种代理方式，适用环境不同：

* 用户代理：本地用户代理，针对于单个用户，适用于物理机或云服务器。
* 全局代理：本地全局代理，针对于整个系统，适用于物理机或云服务器。
* 外部代理：借助外部软件和外部设备实现代理，适用于虚拟机。

下文将以{% inlineImg 316f5eff3a89/clash.png %}为例介绍设置代理的方法。想要丝滑的网络体验，这一步躲不开。

### 用户代理

用户代理只管当前用户，核心就是改 `~/.bashrc`：

1. 准备文件`mihomo-linux-amd64-v1.19.29.gz`、`Country.mmdb`、`config.yaml`。
* `mihomo-linux-amd64-v1.19.29.gz`：从[地址1](https://github.com/MetaCubeX/mihomo/releases)中获取，选择`linux-amd64`版本即可。mihomo 是 Clash 的开源后继项目（原名 Clash.Meta），原版 Clash 已停止维护。
* `Country.mmdb`：从[地址2](https://github.com/Loyalsoldier/geoip/releases)中获取。
* `config.yaml`：从订阅地址中获取，如果下载下来文件后缀是`.yml`，请手动更改为`.yaml`以便后续使用。

三个文件各有分工：`mihomo` 本体是软件，`Country.mmdb` 是 GeoIP 数据库，用来识别流量的目的地，好让规则分流；`config.yaml` 是订阅配置文件。用 `wget` 或 `curl` 下载就行。

```bash
wget <url>
```

2. 把可执行文件解压、重命名、赋予执行权限。

```bash
gunzip mihomo-linux-amd64-v1.19.29.gz   # 解压可执行文件
mv mihomo-linux-amd64-v1.19.29 mihomo   # 重命名
chmod u+x mihomo                        # 为当前用户赋予执行权限
```

3. 把三个文件放进用户目录下的指定位置。

```bash
mkdir ~/.config/mihomo                # 创建配置文件夹
cp Country.mmdb ~/.config/mihomo/     # 复制配置
cp config.yaml ~/.config/mihomo/      # 复制配置
cp mihomo ~/.local/bin/               # 复制可执行文件
```

4. 打开 `~/.bashrc`（终端的启动文件）：

```bash
vim ~/.bashrc
```

文件添加内容如下：

```bash
if ! pgrep -x "mihomo" > /dev/null; then
  nohup ~/.local/bin/mihomo -d ~/.config/mihomo > /dev/null 2>&1 &
fi
```

5. 再用 `export`/`unset` 做一个代理开关注入 `~/.bashrc`，`source` 一下让配置生效。

```bash
vim ~/.bashrc
```

文件添加内容如下：

```bash
function proxy() {
  if [ "$1" = "on" ]; then
    export http_proxy="http://127.0.0.1:7890"
    export https_proxy="http://127.0.0.1:7890"
    export all_proxy="socks5://127.0.0.1:7890"
    echo "Proxy enabled: http://127.0.0.1:7890, socks5://127.0.0.1:7890"
  elif [ "$1" = "off" ]; then
    unset http_proxy
    unset https_proxy
    unset all_proxy
    echo "Proxy disabled."
  else
    echo "Usage: proxy on | off"
  fi
}

# Enable proxy
proxy on > /dev/null 2>&1
```

里面的端口 `7890` 对应 `config.yaml` 里的 `port` 选项，一般就是 7890，不一致的话记得替换。

重新使文件生效：

```bash
source ~/.bashrc
```

从此 `proxy on` 开代理、`proxy off` 关代理。更新订阅配置时，记得先关代理再下载。

### 全局代理

全局代理管整个系统，靠 `systemd` 服务实现，好处是启动、停止、重启都方便管理：

1. 准备文件`mihomo-linux-amd64-v1.19.29.gz`、`Country.mmdb`、`config.yaml`。
* `mihomo-linux-amd64-v1.19.29.gz`：从[地址1](https://github.com/MetaCubeX/mihomo/releases)中获取，选择`linux-amd64`版本即可。mihomo 是 Clash 的开源后继项目（原名 Clash.Meta），原版 Clash 已停止维护。
* `Country.mmdb`：从[地址2](https://github.com/Loyalsoldier/geoip/releases)中获取。
* `config.yaml`：从订阅地址中获取，如果下载下来文件后缀是`.yml`，请手动更改为`.yaml`以便后续使用。

2. 把可执行文件解压、重命名、赋予执行权限。

```bash
gunzip mihomo-linux-amd64-v1.19.29.gz   # 解压可执行文件
mv mihomo-linux-amd64-v1.19.29 mihomo   # 重命名
chmod u+x mihomo                        # 为当前用户赋予执行权限
```

3. 这次要放进系统目录。

```bash
sudo mkdir /etc/mihomo                # 创建配置文件夹
sudo cp Country.mmdb /etc/mihomo/     # 复制配置
sudo cp config.yaml /etc/mihomo/      # 复制配置
sudo cp mihomo /usr/local/bin/        # 复制可执行文件
```

4. 创建系统服务文件，用 `systemctl` 管理。

```bash
sudoedit /etc/systemd/system/mihomo.service
```

> 推荐用 `sudoedit` 而不是 `sudo vim`——它会跟随 `EDITOR` 环境变量选择编辑器，没设置过的话 `export EDITOR=vim` 即可，否则默认可能是 `GNU nano`。

服务文件内容如下：

```service
[Unit]
Description=Mihomo daemon, A rule-based proxy in Go.
After=network.target

[Service]
Type=simple
Restart=always
ExecStart=/usr/local/bin/mihomo -d /etc/mihomo

[Install]
WantedBy=multi-user.target
```

注册并启动服务：

```bash
sudo systemctl enable mihomo          # 设置开机自启
sudo systemctl start mihomo           # 启动系统服务
systemctl status mihomo               # 查看服务状态
```

状态显示 `active` 就成了。

![Clash服务状态](Clash服务状态.png)

5. 代理开关和用户代理一样，加到 `~/.bashrc` 里，`source` 生效。

```bash
vim ~/.bashrc
```

文件添加内容如下：

```bash
function proxy() {
  if [ "$1" = "on" ]; then
    export http_proxy="http://127.0.0.1:7890"
    export https_proxy="http://127.0.0.1:7890"
    export all_proxy="socks5://127.0.0.1:7890"
    echo "Proxy enabled: http://127.0.0.1:7890, socks5://127.0.0.1:7890"
  elif [ "$1" = "off" ]; then
    unset http_proxy
    unset https_proxy
    unset all_proxy
    echo "Proxy disabled."
  else
    echo "Usage: proxy on | off"
  fi
}

# Enable proxy
proxy on > /dev/null 2>&1
```

重新使文件生效：

```bash
source ~/.bashrc
```

同样，`proxy on` 开、`proxy off` 关。

### 外部代理

外部代理是让同一网络里的另一台设备（宿主机）帮忙转发流量。好处是绕开订阅的在线设备数量限制，而且宿主机和虚拟机的代理配置还能保持一致。

用虚拟机（尤其是 WSL）的话，推荐这种方式：

1. 在宿主机安装软件，可使用基于 mihomo 内核的图形化客户端，例如 [Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev)，Windows/macOS/Linux 都支持。

2. 宿主机上按图形界面操作配置，记得**开启局域网访问**（`Allow LAN`）。如果虚拟机连不上，多半是宿主机防火墙拦了代理端口，把对应端口（一般 `7890`）放行即可。

![允许局域网访问](允许局域网访问.png)

3. 查看宿主机IP地址。在Windows下，使用`ipconfig`命令即可。针对于虚拟机，除了内部网络和仅主机模式无法访问网络外，有两种情况：

* NAT模式：选择宿主机与虚拟机相关的虚拟网卡地址，该地址也可在虚拟机中使用`ip route | grep 'default' | awk '{print $3}' | head -n 1`查看。
* 桥接模式：选择宿主机上网时所使用的IP地址，这种情况下通常需要对宿主机设置静态IP地址。

另外，如果 WSL2 开启了镜像网络模式（`.wslconfig` 中的 `networkingMode=mirrored`），宿主机代理直接填 `127.0.0.1:7890` 就行——镜像模式下 localhost 会在 WSL 与 Windows 之间互通；默认的 NAT 模式则要用宿主机 IP。

4. 在虚拟机里把代理开关加到 `~/.bashrc`，`source` 生效。**注意将最后一行进行替换**：

```bash
vim ~/.bashrc
```

文件添加内容如下：

```bash
function proxy() {
  if [ "$1" = "on" ] && [ -n "$2" ]; then
    export http_proxy="http://$2"
    export https_proxy="http://$2"
    export all_proxy="socks5://$2"
    echo "Proxy enabled: http://$2, socks5://$2"
  elif [ "$1" = "off" ]; then
    unset http_proxy
    unset https_proxy
    unset all_proxy
    echo "Proxy disabled."
  else
    echo "Usage: proxy on <address>:<port> | off"
  fi
}

# Enable proxy
proxy on <address>:<port> > /dev/null 2>&1
```

`address` 就是上一步查到的宿主机 IP，`port` 是宿主机 `config.yaml` 里的 `port`，一般 7890。

重新使文件生效：

```bash
source ~/.bashrc
```

之后 `proxy on <address>:<port>` 开、`proxy off` 关。代理本体配置在宿主机上，图形界面点一点就行，很方便。

## 网络排查

配置完还是连不上？按下面的顺序查一遍，大多数问题都能定位：

1. **网关通不通**：`ping <网关地址>`。不通说明本机到路由器的链路有问题，先查网线、网卡和 IP 配置。

2. **有没有默认路由**：`ip route`，看有没有 `default` 开头的行。没有的话，说明路由没配上，检查静态 IP 的网关设置。

3. **DNS 解析正不正常**：`resolvectl status` 查看 DNS 配置，`ping <域名>` 测试解析。解析不了就换 DNS 服务器（`8.8.8.8`、`223.5.5.5` 都行）。

三步下来，基本能定位是物理链路、路由还是 DNS 的问题。剩下的，就是玄学了。
