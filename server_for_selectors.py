# selectorsモジュールを使ってTCPサーバーを作成する
# つまりマルチスレッドなしで実装する
import time
import socket
import sys
import selectors

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

    # selectors
    __selector = selectors.DefaultSelector();

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
        # シングルスレッドの場合,確認用にユーザー名を一時保管する
        self.__accepted_temp_user_names = {}

    @property
    def accepted_sockets(self):
        return self.__accepted_sockets;

    @property
    def accepted_user_names(self):
        return self.__accepted_user_names

    @property
    def accepted_temp_user_names(self):
        return self.__accepted_temp_user_names

    @property
    def selector(self):
        return self.__selector

    @server_report
    def make_server(self):
        """
        サーバーを作成する
        :return:
        """
        s = socket.socket();
        s.bind((self.__server_host, self.__server_port))
        s.listen(self.__backlog);
        self.__server = s;
        # 一応listenまで行ったサーバーsocketを返却する
        return self.__server

    # socketの識別名を返却する
    @staticmethod
    def fetch_socket_identify(client):
        """
        クライアントのIPアドレスとポート番号を取得する
        :param client:
        :return:
        """
        peername = client.getpeername();
        # クライアントのIPアドレスとポート番号を取得する
        client_key = "{}:{}".format(peername[0], peername[1]);
        return client_key

    def run_server(self):
        while True:

            try:
                # 二分ごとに,接続中のクライアント一覧を表示する
                if int(time.time()) % 10 == 0:
                    sys.stdout.write("\r" + str(int(time.time())));

                self.__server.setblocking(False);
                # サーバーへ接続したクライアントをselectors.DefaultSelector()で監視する
                try:
                    (client, address) = self.__server.accept();
                    # クライアントに名前を入力する旨のメッセージを送信する
                    client.send(bytes("最初にあなたの名前を入力して下さい", encoding="utf-8"));
                    client_key = TCPServer.fetch_socket_identify(client);
                    self.accepted_sockets[client_key] = client;
                    # 監視対象に追加する
                    selector_key = self.selector.register(client, selectors.EVENT_READ, client_key)
                    print("監視対象に追加:{}".format(selector_key));
                except BlockingIOError as e:
                    print("{}が発生しました".format(type(e)));

                # クライアントからのSocketの読み取りイベントを監視する
                while True:
                    if len(self.accepted_sockets) == 0:
                        # print("接続中のクライアントがいないため,監視を終了します");
                        break;

                    # シングルスレッドでやる以上タイムアウトの設定は必須
                    active_list = self.selector.select(3);

                    # イベントが発生したSocketを取得する
                    for active_key, mask in active_list:
                        active_socket = active_key.fileobj;

                        # IDEの都合上,型チェックを実行
                        if not isinstance(active_socket, socket.socket):
                            print("active_socketがsocket.socket型ではありません");
                            continue;

                        client_key = TCPServer.fetch_socket_identify(active_socket);

                        # クライアントからのパケットを読み込む
                        total_packets = TCPServer.read_packets(active_socket)

                        # まだクライアントのアカウント名が取得できていない場合
                        if client_key not in self.__accepted_user_names.keys():
                            if client_key in self.__accepted_temp_user_names.keys():
                                if total_packets.decode("utf-8") == "yes":
                                    account_name = self.__accepted_temp_user_names[client_key];
                                    total_packets = bytes("{}さんが入室しました。".format(account_name), encoding="utf-8");
                                    # クライアントのアカウント名を保存する
                                    self.__accepted_user_names[client_key] = account_name
                                    # 一時保存していたアカウント名を削除する
                                    del self.__accepted_temp_user_names[client_key];
                                else:
                                    # クライアントに名前を入力する旨のメッセージを送信する
                                    active_socket.send(bytes("名前の入力は必須項目です。", encoding="utf-8"));
                                    del self.__accepted_temp_user_names[client_key];
                                    continue;
                            else:
                                account_name = total_packets.decode("utf-8");
                                self.__accepted_temp_user_names[client_key] = account_name;
                                active_socket.send(bytes("あなたの名前は[{}]さんでよろしいですか? <yes or no>".format(account_name), encoding="utf-8"));
                                continue

                        print("Start broadcast.")
                        # broadcastを実行
                        self.broadcast_message(client_key, total_packets)
                    break;
            except Exception as e:
                # 例外が発生した場合は,アプリケーションを終了する
                print("Fatal Error has occurred.")
                exit(-1);

    @staticmethod
    def read_packets(client) -> bytes:
        """
        引数に指定したSocketからパケットを読み込む.かつ,読み込んだパケットを返却する
        :param client:
        :return:
        """
        # bytes型で初期化
        total_packets = b"";
        client.setblocking(False);
        while True:
            try:
                # もしBUFFER_SIZEの倍数のパケットが送信された場合
                # ブロッキングIOだとパケットを全て取得できないため
                # ノンブロッキングIOに設定する
                # 指定バイト数分取得
                temp = client.recv(BUFFER_SIZE)
                total_packets += temp;
                print(temp);
                if len(temp) < BUFFER_SIZE:
                    break;
            except BlockingIOError as e:
                print("BlockingIOErrorが発生しました");
                if len(total_packets) > 0:
                    print("パケットの取得が完了しました");
                    break;
                else:
                    print("パケットの取得に失敗しました");
                    break;
            except Exception as e:
                print(type(e))
                break;
        return total_packets


    @staticmethod
    def fetch_user_name(client, client_key):
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

    # 特定のユーザーの発言を他のユーザーにブロードキャストする
    def broadcast_message(self, client_key, packets) -> int:
        """
        発言者以外の全クライアントにメッセージを送信する
        :param client_key: 発言者の識別名
        :param packets: 発言者の発言内容
        :return:
        """
        print("Start broadcast to clients that are alive.")
        count_for_sent_packets = 0;
        for key in list(self.__accepted_sockets):
            if key == client_key:
                continue;
            try:
                self.__accepted_sockets[key].send(packets);
                count_for_sent_packets += 1;
            except Exception as e:
                print(e);
                # 接続済み配列から現ループのkeyを削除する
                del self.__accepted_sockets[key];
        return count_for_sent_packets;

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
