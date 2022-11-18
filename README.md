# video-server

![image](https://user-images.githubusercontent.com/6856673/200156099-9cc88e99-8ed9-46e5-99aa-499e053cddb2.png)

An open source video server which uses WebTorrent to turn your viewers into decentralized rebroadcasters. Fallback players for clients that can't support webtorrent.

[![Actions Status](https://github.com/zackees/webtorrent-movie-server/workflows/MacOS_Tests/badge.svg)](https://github.com/zackees/webtorrent-movie-server/actions/workflows/push_macos.yml)
[![Actions Status](https://github.com/zackees/webtorrent-movie-server/workflows/Win_Tests/badge.svg)](https://github.com/zackees/webtorrent-movie-server/actions/workflows/push_win.yml)
[![Actions Status](https://github.com/zackees/webtorrent-movie-server/workflows/Ubuntu_Tests/badge.svg)](https://github.com/zackees/webtorrent-movie-server/actions/workflows/push_ubuntu.yml)

# Installation

  * Environmental variables
    * PASSWORD - set to your password
    * DOMAIN_NAME - set this to the url without the http:// part
    * WEBTORRENT_ENABLED - set to 0 to disable
    * DATA_ROOT: /var/data
      * The persistant disk thats mounted into docker.

It should look like this:
![image](https://user-images.githubusercontent.com/6856673/202430544-5dfd89aa-2048-445f-9bc9-85c02e778462.png)

With an external disk like this:

![image](https://user-images.githubusercontent.com/6856673/202666533-71bcb5c0-cc84-4d18-8f04-1d13fa945130.png)

