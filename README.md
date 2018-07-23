# rj
rjはLinuxでのTV録画予約用コマンドラインスクリプトです。
バックエンドのジョブスケジューラには、[systemd timer](https://www.freedesktop.org/software/systemd/man/systemd.timer.html)または[TORQUE Resource Manager](http://www.adaptivecomputing.com/products/torque/)が使用できます。

実行にはPython 3.5以降が必要です。

## Install

NOTE: チューナーデバイスのドライバとrecpt1コマンドのセットアップは完了しているものとします。

GitHubのリポジトリからcloneします。
```bash
git clone https://github.com/sw37th/rj.git
```

依存するPythonライブラリをインストールします。今のところ、rjはPyYAMLとdocoptを使用します。
```bash
sudo apt install python3-yaml python3-docopt
```

## Set up

~/.config/systemd/userディレクトリが存在しない場合は作成します。
```bash
mkdir -m 700 ~/.config
mkdir -m 755 ~/.config/{systemd,systemd/user}
```

NOTE: ~/.configディレクトリは次回ログイン時から利用できます。一旦ログアウトし、再ログインしてください。

~/.rjディレクトリを作成し、channel.ymlファイルを配置します。
```bash
mkdir ~/.rj
cp rj/channel.yml ~/.rj
```

~/.rj/channel.ymlを編集し、お住いの地域の物理チャンネル番号とテレビ局名に変更します。
( https://ja.wikipedia.org/wiki/テレビ周波数チャンネル )
```bash
vi ~/.rj/channel.yml
```

~/recディレクトリを作成します。録画ファイルはこのディレクトリに作成されます。
```bash
mkdir ~/rec
```

## Usage

```bash
Usage:
  rj add [-r|--repeat <TYPE>] CH TITLE DATE TIME [RECORDINGTIME]
  rj del JOBID [JOBID...]
  rj list [DATE]
  rj show JOBID
  rj modbegin JOBID (DELTATIME | DATE TIME)
  rj totalrec JOBID RECORDINGTIME
  rj extendrec JOBID DELTATIME
  rj setrep JOBID TYPE
  rj unsetrep JOBID
  rj listch rj -h | --help

Options:
  -h --help            :show this screen.
  -r --repeat <TYPE>   :set repeat flag. TYPE can specify 'weekly', 'daily', 'weekday', 'asadora'
```

rj addで録画予約をサブミットします。
例えば月曜日の26:30から15分間、BS11(211チャンネル)にて放送される「ヤマノススメ サードシーズン」を録画する場合、
```bash
./rj add 211    yamanosusume_3rd  Mon  26:30 00:15:00
```

rj listでサブミット済みの録画予約ジョブを一覧表示します。

```bash
./rj list
ID       Ch             Title                    Start           walltime rep tuner
-------- -------------- ------------------------ --------------- -------- --- -----
e2156ff5 211 BS11       yamanosusume_3rd         Mon  7/23 26:30 00:15:00     bs     
```

録画予約ジョブの削除はrj delを実行します。

```bash
./rj del e2156ff5
```

デフォルトでは予約した録画が完了するとジョブは削除されます。同じジョブを繰り返し実行する場合はリピートフラグをセットします。

```bash
./rj setrep e2156ff5 weekly
```

リピートフラグは 'weekly', 'daily', 'weekday', 'asadora' の4種類があります。

| Flag    | Periodically |
----------|---------------
| weekly  | 毎週         |
| daily   | 毎日         |
| weekday | 月曜から金曜 |
| asadora | 月曜から土曜(NHK朝ドラ用) |

rj unsetrepでリピートフラグを外せます。

```bash
./rj unsetrep e2156ff5
```
