import socket
import random
import sys

def read_file(file_path):
    with open(file_path, 'r') as file:
        return file.read()

def send_initialization(client_socket, N):
    initialization_packet = b'\x00\x01' + N.to_bytes(4)  #Initialization报文
    client_socket.send(initialization_packet)
    response = client_socket.recv(2)
    if response == b'\x00\x02': #agree报文
        print("服务器同意初始化")
    else:
        print("服务器拒绝初始化")
        return;

def send_reverse_request(client_socket, data):
    length = len(data)

    reverse_request_packet = b'\x00\x03' + length.to_bytes(4) + data.encode()
    client_socket.send(reverse_request_packet)
    response = client_socket.recv(1024)
    type_field = response[0:2]

    if type_field == b'\x00\x04':  # ReverseAnswer报文
        reversed_length = int.from_bytes(response[2:6])
        reversed_text = response[6:6+reversed_length].decode()
        return reversed_text
    else:
        print("服务器无响应")
        return

def main(server_ip, server_port, Lmin, Lmax, file_path):
    server_address = (server_ip, server_port)
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    client_socket.connect(server_address)

    original_text = read_file(file_path)

    total_l = len(original_text)
    block_ls = []
    remaining_l = total_l

    while remaining_l> 0:
        if remaining_l > Lmax:
            block_l = random.randint(Lmin, Lmax)
        else:
            block_l = remaining_l

        block_ls.append(block_l)
        remaining_l -= block_l

    N = len(block_ls)

    send_initialization(client_socket, N)

    reversed_texts = []
    start_index = 0
    for i, block_l in enumerate(block_ls): #转化为枚举对象
        block_text = original_text[start_index:start_index + block_l]
        reversed_text = send_reverse_request(client_socket, block_text)
        print(f"{i+1}: {reversed_text}")
        reversed_texts.append(reversed_text)
        start_index += block_l

    with open("reversed_output.txt", "w") as f:
        f.write(''.join(reversed_texts))

    client_socket.close()

if __name__ == "__main__":
    if len(sys.argv) != 5:
        print("请按照以下格式输入： <server_ip> <server_port> <Lmin> <Lmax>")
        sys.exit(1)

    server_ip = sys.argv[1]
    server_port = int(sys.argv[2])
    Lmin = int(sys.argv[3])
    Lmax = int(sys.argv[4])
    file_path = "readme.txt"

    main(server_ip, server_port, Lmin, Lmax, file_path)