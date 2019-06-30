# FirefoxCache2
## 文件目录结构

Firefox在用户的profile目录中保存缓存文件结构，可以通过在firefox地址输入框中输入'about:profiles'查看当前用户的profile目录。

在profile中找到'cache2'目录，该目录保存了浏览器的缓存数据。其中主要内容有两个：

1. 'index'文件：该文件是缓存的索引文件，记录了每一个被缓存在本地磁盘上的缓存文件的基本元信息，比如缓存记录的使用频率、过期时间、文件大小等...
2. 'entries'目录：目录中的每一个文件对应一个被浏览器缓存的数据文件，并且文件使用特定的数据格式存储了相应的元信息，比较重要的信息有URL


```
$ ls
AlternateServices.txt        cache2                       extensions.json              pkcs11.txt                   startupCache
OfflineCache                 cert9.db                     favicons.sqlite              places.sqlite                storage
SecurityPreloadState.txt     compatibility.ini            formhistory.sqlite           pluginreg.dat                storage-sync.sqlite
SiteSecurityServiceState.txt containers.json              gmp                          prefs.js                     storage.sqlite
TRRBlacklist.txt             content-prefs.sqlite         gmp-gmpopenh264              safebrowsing                 thumbnails
addonStartup.json.lz4        cookies.sqlite               gmp-widevinecdm              saved-telemetry-pings        times.json
addons.json                  crashes                      handlers.json                search.json.mozlz4           weave
blocklist.xml                datareporting                key4.db                      sessionCheckpoints.json      webappsstore.sqlite
bookmarkbackups              extension-preferences.json   minidumps                    sessionstore-backups         webappsstore.sqlite-shm
broadcast-listeners.json     extensions                   permissions.sqlite           sessionstore.jsonlz4         xulstore.json


$ ls cache2/
doomed    entries   index     index.log

$ ls cache2/entries/
017239BD353C39FEF561AD4878BC169D5B89D5FA 5D032C390BFDCC43406BE001CADB00C017762B77 B25D0FBB9AD160F3CA160ED3E26BFF9F0E274929
026860131AC8837A36968B435E640BDD30992E73 5D2DC9AE83B62B8763A0C14BDB89C4C45EFA111D B2BB561C0A27E72044D3AEE5425F4E5A8F0348E2
04465FB4C96F61466B9A67422B84ECC5F3EDEBC6 5E4954707B44E5A4B4ACF5F22B52219A1DCA477F B35B9720DB46BE7509AD4A253DDA32F12CEFFBC8
04978A7A83CF7B8511841F4A26598987807DBC89 5F34A74D1380D10E61240C4B94321E6D5B7812DB B412652745622FCEAC058F3F08A728999A3B4664
04D7BC87034DE29F67E22BAA58D84F3D1C64E15A 5FE950976304D0FC774A22F674AF6B00E8528C88 B4160F7B008034AC71D5F250245DFE39FBEEC360
06B62E73358EF1CBB9F8B4068FB133EE20D83FBF 601487B53548B7563ABB522C9452E066D0E8F82B B428F0BFE97CCBEF8F796B282FAF44664A4B0328
07D9B3A9557270C7517C771711663C8F78019C12 6059AD83AC6E3CFF4FEE798D7BD32709ED3F51DE B45040B5F7F65C61AF516477B393B2C3129BEA9A
0843F8C54EDE9BDFABABDB50655BB7CD89945828 609B40F6174E219E48CD0A82ECF3ADE83FFE90B6 B4E19E0CA4676E3E873F580DB210101AB849FBA6
...
```


## 缓存index文件格式

文件使用Big-endian字节序，文件由1个文件头及后续多个描述缓存文件的数据块构成，每一块描述一个对应的缓存文件。

|偏移|Size|内容|
|---|---|---|
|0x0| 12 Bytes | 文件头 |
|0xC| 36 Bytes | 第一个缓存文件描述块 |
|0x30| 36 Bytes| 第二个缓存文件描述块 |
| ... | ... | ... |
|0xC+N*0x24|36 Bytes|第N个缓存文件描述块|


文件头具体结构如下：

|偏移|size|内容|
|---|---|---|
|0x0|4 Bytes |版本号|
|0x4|4 Bytes|最后一次更新时间戳|
|0x8|4 Bytes|脏数据标记|


每一个缓存描述块内部结构如下：

|内部偏移|size|内容|
|---|---|---|
|0x0|20 Bytes|缓存文件key（':'+URL）的sha1|
|0x14|4 Bytes|使用频率|
|0x18|4 Bytes|过期时间|
|0x1C|4 Bytes|app ID|
|0x20|1 Bytes|缓存文件flag|
|0x21|3 Bytes|缓存文件大小|


## 缓存文件格式

'cache2/entries'目录中的每个文件用来记录一个被缓存的文件，文件内容也是Big-endian，文件格式如下：

|偏移|size|内容|
|---|---|---|
|0x0|缓存文件大小|被缓存文件内容|
|紧接着缓存数据|4+n_chunk*2|暂时还不清楚其中具体内容，不过文件URL信息不在其中|
|紧接着上面的位置|可变长度|被缓存文件元信息|
|文件最后|4 Bytes|被缓存文件内容的尺寸|

n_chunk的计算方法是“(被缓存文件尺寸+256k-1)/256k”。

从上面的结构看，解析缓存文件第一步就是从最后4个字节找到缓存文件尺寸，从而找到对应的元信息。元信息中包含了最重要的缓存文件的key ID信息，key ID包含了缓存数据的URL。

元信息格式：

|内部偏移|尺寸|内容|
|---|---|---|
|0x0|4 Bytes|版本信息|
|0x4|4 Bytes|被获取数量|
|0x8|4 Bytes|上次获取时间戳|
|0xC|4 Bytes|上次修改时间戳|
|0x10|4 Bytes|超时时间戳|
|0x14|4 Bytes|key的字节长度|
|0x18|4 Bytes|标志位信息|
|0x1C|0x14中的key尺寸|key信息|
|...|...|...|
|...|...|请求信息|


