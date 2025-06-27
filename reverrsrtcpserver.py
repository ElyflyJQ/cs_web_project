import socket
import threading

def reverse_string(s):
    return s[::-1]

def handle_client(client_socket):
    while True:
        try:
            data = client_socket.recv(1024)
            if not data:
                break

            type_field = data[0:2]
            
            if type_field == b'\x00\x01':  #Initialization报文
                N = int.from_bytes(data[2:6])
                print(f"预计收到{N}块数据")
                client_socket.send(b'\x00\x02')  #Agree报文

            elif type_field == b'\x00\x03':  #ReverseRequest报文
                length = int.from_bytes(data[2:6])
                text = data[6:6+length].decode()
                reversed_text = reverse_string(text)

                response = b'\x00\x04' + len(reversed_text).to_bytes(4) + reversed_text.encode()
                client_socket.send(response)
        except Exception as e:
            print(f"处理客户端时出错: {e}")
            break

    client_socket.close()

def start_server(server_ip, server_port):
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((server_ip, server_port))
    server_socket.listen(5)
    print(f"服务器正在监听 {server_ip}:{server_port}")

    while True:
        client_socket, addr = server_socket.accept()
        print(f"接受来自 {addr} 的连接")
        # 创建新线程
        client_handler = threading.Thread(target=handle_client, args=(client_socket,))#元组
        client_handler.start()

if __name__ == "__main__":
    server_ip = "127.0.0.1"
    server_port = 8888
    start_server(server_ip, server_port)