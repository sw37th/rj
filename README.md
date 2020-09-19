# rj
rjはLinuxでのTV録画予約用コマンドラインスクリプトです。
バックエンドのジョブスケジューラーは下記のいずれかが選択できます。

* [OpenPBS](https://www.openpbs.org/)
* [systemd timer](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)
* [TORQUE Resource Manager](https://github.com/adaptivecomputing/torque)

実行にはPython 3.6以降が必要です。

## Install

NOTE: チューナーデバイスのドライバとrecpt1コマンドのセットアップは完了しているものとします。

GitHubのリポジトリからcloneします。
```
$ git clone https://github.com/sw37th/rj.git
```

依存するPythonライブラリをインストールします。今のところ、rjはPyYAMLを使用します。
```
$ sudo apt install python3-yaml
```

## Set up

### スケジューラーにSystemdを使用する場合

`~/.config/systemd/user`ディレクトリが存在しない場合は作成します。
```
$ mkdir -m 700 ~/.config
$ mkdir -m 755 ~/.config/{systemd,systemd/user}
```

NOTE: `~/.config`ディレクトリは次回ログイン時から利用できます。一旦ログアウトし、再ログインしてください。

### 全スケジューラー共通

`~/.rj`ディレクトリを作成し、`channel.yml`ファイルを配置します。
```
$ mkdir ~/.rj
$ cp rj/channel.yml ~/.rj
```

`~/.rj/channel.yml`を編集し、お住いの地域の物理チャンネル番号とテレビ局名に変更します。
( https://ja.wikipedia.org/wiki/テレビ周波数チャンネル )
```
$ vi ~/.rj/channel.yml
```

`~/rec`ディレクトリを作成します。録画ファイルはこのディレクトリに作成されます。
```
$ mkdir ~/rec
```

## Usage

```
usage: rj [-h]
          {add,del,list,show,modbegin,modrectime,modch,modname,chlist} ...

positional arguments:
  {add,del,list,show,modbegin,modrectime,modch,modname,chlist}
    add                 add TV recording JOB
    del                 delete JOBs
    list                list JOBs
    show                show JOB information
    modbegin            change start time
    modrectime          change recording time
    modch               change channel of program
    modname             change title name of program
    chlist              list TV station name

optional arguments:
  -h, --help            show this help message and exit
```

### 録画予約の作成

`rj add`で録画を予約します。
```
usage: rj add [-h] ch name date time [rectime]

positional arguments:
  ch          channel number
  name        program name
  date        airdate
  time        airtime
  rectime     recording time
```
例えば月曜日の26:30から15分間、BS11(211チャンネル)にて放送される「ヤマノススメ サードシーズン」を録画する場合、
```
$ ./rj add 211    yamanosusume_3rd  Mon  26:30 00:15:00
```

### 予約確認

`rj list`で録画予約を一覧表示します。
```
usage: rj list [-h] [date]

positional arguments:
  date        airdate
```

デフォルトではすべての録画予約が表示されます。

```
$ ./rj list
ID    Channel        Title                    Start           Rectime  User     Tuner
----- -------------- ------------------------ --------------- -------- -------- -----
258   15  MX         yurukyan                 Mon 09/21 22:30 00:29:30 autumn   tt
261   211 BS11       yamanosusume_3rd         Mon 09/21 26:30 00:15:00 autumn   bs
----- -------------- ------------------------ --------------- -------- -------- -----
260   15  MX         hokago_teibounisshi      Tue 09/22 24:30 00:29:30 autumn   tt
----- -------------- ------------------------ --------------- -------- -------- -----
259   15  MX         rezero_2nd               Wed 09/23 23:30 00:29:30 autumn   tt
```

日付や曜日指定もできます。

```
$ ./rj list 9/22
ID    Channel        Title                    Start           Rectime  User     Tuner
----- -------------- ------------------------ --------------- -------- -------- -----
260   15  MX         hokago_teibounisshi      Tue 09/22 24:30 00:29:30 autumn   tt

$ ./rj list Mon
ID    Channel        Title                    Start           Rectime  User     Tuner
----- -------------- ------------------------ --------------- -------- -------- -----
258   15  MX         yurukyan                 Mon 09/21 22:30 00:29:30 autumn   tt
261   211 BS11       yamanosusume_3rd         Mon 09/21 26:30 00:15:00 autumn   bs
```

### 予約削除

`rj del`で録画予約を削除します。

```
$ ./rj del 262
Delete JOB:
ID    Channel        Title                    Start           Rectime  User     Tuner
----- -------------- ------------------------ --------------- -------- -------- -----
262   15  MX         gibiate                  Wed 09/23 22:00 00:29:30 autumn   tt
```
