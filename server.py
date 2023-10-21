import select
import socket;
import threading;
import sys

# クライアントからメッセージを受信するバイトサイズ
BUFFER_SIZE = 16
arguments = sys.argv;

if len(arguments) < 3:
    # 引数が足りない場合はデフォルトのIPアドレスとポート番号を指定
    server_host = "127.0.0.1"
    server_port = 11180;
    server_backlog = 256
else:
    # コマンド実行時の引数からサーバー側のIPアドレスとポート番号を指定
    (server_host, server_port, server_backlog) = (arguments[1], int(arguments[2]), int(arguments[3]));


def server_report(function):
    def wrapper(*args, **kwargs):
        print("decoratorでラップされた関数が実行されました");
        return function(*args, **kwargs);

    return wrapper


class TCPServer:

    # サーバー側で生成したスレッドを保持
    # {socket name : thread}
    __thread_list = {};
    def __init__(self, host, port, backlog):
        self.__server_host = host
        self.__server_port = port
        self.__backlog = backlog;
        # defaultでは設定しない
        self.__server = None;
        # 当該サーバーに接続して許可されたSocket一覧を保持
        self.__accepted_sockets = {};
        # クライアントごとのユーザー名を保持
        self.__accepted_user_names = {}

    @property
    def accepted_sockets(self):
        return self.__accepted_sockets;

    @property
    def accepted_user_names(self):
        return self.__accepted_user_names

    @server_report
    def make_server(self, callback=None):
        """
        サーバーを作成する
        :type callback: callable
        :param callback:
        :return:
        """
        if callable(callback):
            callback(self.__server_host, self.__server_port, self.__backlog);

        s = socket.socket();
        s.bind((self.__server_host, self.__server_port))
        s.listen(self.__backlog);
        self.__server = s;
        # 一応listenまで行ったサーバーsocketを返却する
        return self.__server

    def run_server(self):
        while True:
            print("[クライアントを受付中...]");
            print(">> 現在接続中クライアント一覧");
            for key in list(self.__accepted_user_names):
                print("Socket名[{}],ユーザー名[{}]".format(key, self.__accepted_user_names[key]))
            print(">> 接続中クライアント一覧終了");

            (client, address) = self.__server.accept();
            client_key = "{}:{}".format(address[0], address[1])

            # スレッドを新規作成して,メインスレッドのブロックを防ぐ
            self.__thread_list[client_key] = threading.Thread(target=self.handler, args=(client, client_key))
            self.__thread_list[client_key].start();

    # 指定バイト数分ずつ読み込んで,Socketからパケットを取得する
    @staticmethod
    def read_packets(client) -> str:
        packets = b"";
        # while True:

        number = select.select([client], [], []);
        read_list = number[0];

        for read in read_list:
            while True:
                try:
                    # socketをノンブロッキングに設定する
                    read.setblocking(False)
                    data = read.recv(BUFFER_SIZE)
                    packets += data;
                    if len(data) == 0:
                        break;
                    if len(data) < BUFFER_SIZE:
                        break
                except BlockingIOError as e:
                    print("★BlockingIOErrorが発生しました");
                    print("読み取り完了です")
                    # ノンブロッキングの場合は例外がスローされるため
                    # 例外発生時 == 読み込み完了とする
                    if len(packets) > 0:
                        break;

            # データ受信時以外はノンブロッキングを解除する
            read.setblocking(True)
        # client socketからの戻り値は bytes型なのでstr型に変換する
        decoded_packets = packets.decode("utf-8");
        return decoded_packets

    def fetch_user_name(self, client, client_key):
        """
        初回Socketからの読み込みのみユーザー名を取得する
        :param client:
        :param client_key:
        :return:
        """
        while True:
            # clientへwelcomeメッセージを送信する
            client.send(bytes("最初にあなたの名前を入力して下さい", encoding="utf-8"));
            # clientからの入力を受け取る
            user_name = TCPServer.read_packets(client)
            print("受け取ったユーザー名[{}]".format(user_name))
            if len(user_name) == 0:
                print("入力内容が空です");
                continue;

            # 入力内容が空でない場合
            question_message = "あなたの名前は[{}]ですか?  <yes or no>".format(user_name);
            print(question_message);
            client.send(bytes(question_message, encoding="utf-8"))
            # yes or noの入力を受け取る
            answer = TCPServer.read_packets(client);
            print("受け取った回答[{}]".format(answer))
            if answer == "yes":
                print("ユーザー名を確定しました");
                break;
            else:
                print("ユーザー名の受信に失敗しました")

        return user_name

    def handler(self, client, client_key):
        """
        クライアントからのメッセージを受信する
        :param client:
        :param client_key:
        :return:
        """
        # ユーザー名を取得する
        user_name = self.fetch_user_name(client, client_key);

        # clientのユーザー名を一旦出力
        print("接続したユーザー名は[{}]です".format(user_name));

        client.send(bytes("[{}]さん,TCPサーバーへようこそ".format(user_name), encoding="utf-8"));

        # (1).当該ユーザーが他ユーザーにログインしたことを通知する.
        # (2).Socketからの初回メッセージの場合は取得したメッセージをユーザー名として扱う.
        # (3).名前を確定したら,サーバーのメンバにSocketオブジェクトと名前を追加する
        if not self.__accepted_user_names.get(client_key):
            self.__accepted_user_names[client_key] = user_name;
            self.__accepted_sockets[client_key] = client

        self.broadcast_message(client_key, "[{}]さんが入室しました".format(user_name))

        while True:
            # 小分けにして受け取ったパケットを結合するため
            packets = TCPServer.read_packets(client);
            # パケットが読み取れた場合のみ処理を行う
            if len(packets) > 0:
                self.broadcast_message(client_key, packets);

    # 特定のユーザーの発言を他のユーザーにブロードキャストする
    def broadcast_message(self, client_key, packets):
        print("broadcast_message スタート");
        print(self.__accepted_sockets);
        for key in list(self.__accepted_sockets):
            # 送信したいパケットを初期化
            # 自分のSocketクライアントにはメッセージを送信しない
            if key == client_key:
                continue;
            # 自分以外のSocketクライアントにメッセージを送信する
            user_name = self.__accepted_user_names[client_key];

            # パケットは\r\n(改行)区切りで送信する
            # 偶数行は発信者名,奇数行は発言内容とする
            initial_packets = "{}\r\n{}\r\n".format(user_name, packets);
            try:
                # client側から意図的に接続をきられた場合は例外がスローされるため
                # その場合は接続済み配列から現ループのkeyを削除する
                self.__accepted_sockets[key].send(bytes(initial_packets, encoding="utf-8"));
                # 送信した後に空文字を送信することで
                # クライアント側のrecv()メソッドのブロックを解除する
                self.__accepted_sockets[key].send(bytes("", encoding="utf-8"));
            except Exception as e:
                print(e);
                # 接続済み配列から現ループのkeyを削除する
                del self.__accepted_sockets[key];
                del self.__accepted_user_names[key];

    # サーバーからのレスポスンスを定義するためのメソッド
    @staticmethod
    def formatter_for_packets(user_name, packets):
        temp = [user_name, packets];
        temp = "\r\n".join(temp) + "\r\n";
        return "".join(temp)


if __name__ == "__main__":
    tcp_server = TCPServer(server_host, server_port, server_backlog)
    tcp_server.make_server()
    tcp_server.run_server()
