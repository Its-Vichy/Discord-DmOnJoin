import threading, os, json, httpx, itertools, string, sys, time, discum, re
from colorama import Fore, init; init()

lock = threading.Lock()
tk = open('./tokens.txt', 'r+').read().splitlines()
__tokens__ = itertools.cycle(tk)
__proxies__ = itertools.cycle(open('./proxies.txt', 'r+').read().splitlines())
__config__ = json.load(open('./config.json', encoding='utf-8', errors='ignore'))

class Data:
    def __init__(self):
        self.blacklist = []
        self.dead = []

        self.dm = 0
    
    def refresh_file(self, user_id: str):
        with open('./dm.txt', 'a+') as f:
            f.write(f'{user_id}\n')
        
        open('./tokens.txt', 'w').truncate(0)
        with open('./tokens.txt', 'a+') as tf:
            for token in tk:
                if token not in self.dead:
                    tf.write(f'{token}\n')


data = Data()


class Console:
    @staticmethod
    def printf(content: str):
        lock.acquire()
        print(content.replace('[+]', f'[{Fore.LIGHTGREEN_EX}+{Fore.RESET}]').replace('[*]', f'[{Fore.LIGHTYELLOW_EX}*{Fore.RESET}]').replace('[>]', f'[{Fore.CYAN}>{Fore.RESET}]').replace('[-]', f'[{Fore.RED}-{Fore.RESET}]'))
        lock.release()
    
    @staticmethod
    def print_logo():
        os.system('cls' if os.name == 'nt' else 'clear')
        print(Fore.LIGHTWHITE_EX + """
        by github.com/its-vichy                      
        """)


class ReactionListener(threading.Thread):
    def __init__(self):
        client = discum.Client(token= __config__['listenner_token'], log=False)

        @client.gateway.command
        def ws(resp):
            if resp.event.ready_supplemental:
                user = client.gateway.session.user
                Console.printf("[+] Listenning -> {}#{}".format(user['username'], user['discriminator']))
                client.gateway.subscribeToGuildEvents(False)

            if resp.event.message:
                m = resp.parsed.auto()
                content = m['content']
                channelID = m['channel_id']

                if channelID == __config__['welcome_channel_id']:
                    time.sleep(__config__['wait_time'])
                    for ids in re.findall(r'<@[!|\S][0-9]+>', content):
                        if ids not in data.blacklist:
                            ids = str(ids).split('<@!' if '<@!' in content else '<@')[1].split('>')[0]
                            data.blacklist.append(ids)
                            self.send_dm(ids)
                            data.refresh_file(ids)

        client.gateway.run()

    def send_dm(self, user_id: str):
        token = None
        while True:
            if len(data.dead) == len(tk):
                Console.printf("[!] All token dead.")
                sys.exit(0)

            token = next(__tokens__)
            if token not in data.dead:
                break
            
        with httpx.Client(proxies='http://'+next(__proxies__) if __config__['proxy'] else None, timeout=__config__['timeout'], headers={'Authorization': str(token), "accept":"*/*", "accept-language":"en-GB", "content-type":"application/json", "cookie":f"__dcfduid=edc66f70a13b11ecbc29b528c335c9a8; __sdcfduid=edc66f71a13b11ecbc29b528c335c9a8fbd107f398e4ac46430be6b2ef50f65b1767e9f5135f04809f1a376bc649318c; locale=en-US", "origin":"https://discord.com", "sec-fetch-dest":"empty", "sec-fetch-mode":"cors", "sec-fetch-site":"same-origin", "user-agent":"Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) discord/1.0.9003 Chrome/91.0.4472.164 Electron/13.4.0 Safari/537.36", "x-debug-options":"bugReporterEnabled", "x-super-properties":"eyJvcyI6IldpbmRvd3MiLCJicm93c2VyIjoiRGlzY29yZCBDbGllbnQiLCJyZWxlYXNlX2NoYW5uZWwiOiJzdGFibGUiLCJjbGllbnRfdmVyc2lvbiI6IjEuMC45MDAzIiwib3NfdmVyc2lvbiI6IjEwLjAuMjI0NjMiLCJvc19hcmNoIjoieDY0Iiwic3lzdGVtX2xvY2FsZSI6InNrIiwiY2xpZW50X2J1aWxkX251bWJlciI6OTkwMTYsImNsaWVudF9ldmVudF9zb3VyY2UiOm51bGx9"}) as client:
            response = client.post(f'https://discord.com/api/v9/users/@me/channels', json= {"recipient_id": user_id})        
    
            if response.status_code in [403, 401, 405]:
                Console.printf(f"[-] Token locked/dead: {token}")
                data.dead.append(token)
            elif response.status_code == 200:
                dm_response = client.post(f'https://canary.discord.com/api/v9/channels/{response.json()["id"]}/messages', json={"content": __config__['message'].replace("<user>", f"<@{user_id}>").replace('<newline>', '\n'), "tts": False})

                if dm_response.status_code == 200:
                    data.dm += 1
                    Console.printf(f"[+] Dm sent to {user_id} - {token} [{data.dm}]")
                else:
                    if dm_response.status_code == 403:
                        err_code = dm_response.json()['code']
                        
                        if err_code == 40007:
                            Console.printf(f"[-] dm closed {user_id} - {token} [{data.dm}]")
                        elif err_code == 40002:
                            Console.printf(f"[-] Token locked {user_id} - {token} [{data.dm}]")
                        elif err_code == 40003:
                            Console.printf(f"[*] Token Ratelimited {user_id} - {token} [{data.dm}]")
                            self.send_dm(user_id)

    # return bad cookie lenght err
    def randstr(self, lenght: int):
        return ''.join([string.ascii_lowercase + string.ascii_letters + string.ascii_uppercase + string.digits for _ in range(lenght)])

if __name__ == '__main__':
    Console.print_logo()
    ReactionListener().start()
