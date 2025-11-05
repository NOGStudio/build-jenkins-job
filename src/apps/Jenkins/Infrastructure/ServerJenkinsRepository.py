import jenkins
import json
import requests
import time
from src.apps.Jenkins.Domain.ServerRepository import ServerRepository
from src.apps.Jenkins.Domain.JobParams import JobParams

import re
from requests.auth import HTTPBasicAuth

ANSI_RE = re.compile(r'\x1b\[[0-9;]*[A-Za-z]')

def _sanitize_bytes(b: bytes) -> str:
    # Décodage robuste pour AFFICHAGE (pas pour l’offset)
    for enc in ('utf-8', 'cp1252', 'latin-1'):
        try:
            s = b.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        s = b.decode('utf-8', 'replace')
    # Normalise CR/LF et enlève l’ANSI
    s = s.replace('\r\n', '\n').replace('\r', '\n')
    return ANSI_RE.sub('', s)

class ServerJenkinsRepository(ServerRepository):
    def __init__(self, url: str, token: str, username: str, ssl_verify=False, timeout=180):
        self.__url = url
        self.__token = token
        self.__username = username
        self.__ssl_verify = ssl_verify
        self.__timeout = timeout

        # Start Connection
        self.__connection = jenkins.Jenkins(self.__url, username=self.__username, password=self.__token, timeout=self.__timeout)
        self.__connection._session.verify = ssl_verify
        
    def build(self, name: str, params: JobParams) -> None:
        self.__name = name
        queue_id = self.__connection.build_job(name, parameters=json.loads(params), token=self.__token)
        self.__queue_id = queue_id

    def __get_queue_info(self):
        protocol, domain = self.__url.split("://")
        url = f"{protocol}://{self.__username}:{self.__token}@{domain}/queue/item/{self.__queue_id}/api/json?pretty=true"
        info = requests.get(url, verify=self.__ssl_verify).json()
        return info

    def get_number(self) -> int:
        while "executable" not in (info := self.__get_queue_info()):
            time.sleep(3)
        return info["executable"]["number"]

    def get_status(self, number) -> str:
        attempts = 3
        for attempt in range(attempts):
            try:
                build_info = self.__connection.get_build_info(name=self.__name, number=number)
                return build_info["result"]
            except jenkins.JenkinsException as e:
                print(f"Attempt {attempt + 1} of {attempts} failed: {e}")
                if attempt < attempts - 1:
                    time.sleep(5)  # Wait for 5 seconds before retrying
                else:
                    print(f"Job [{self.__name}] number [{number}] does not exist after {attempts} attempts. Continuing as non-fatal error.")
                    return "UNKNOWN"
    
    def get_build_console_output(self, name, number):
        return self.__connection.get_build_console_output(name, number)


    def stream_build_console_output(self, name: str, number: int) -> str:
        """
        Stream le log console en utilisant /logText/progressiveText jusqu'à la fin du build.
        Retourne le statut final (SUCCESS/FAILURE/ABORTED/UNSTABLE/UNKNOWN).
        """
        start = 0
        # force un stdout UTF-8 pour GitHub Actions
        try:
            import sys
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except Exception:
            pass

        while True:
            # Récupère l'URL exacte du build (gère espaces/dossiers)
            build_url = self.__connection.get_build_info(name, number)['url']
            url = f"{build_url}logText/progressiveText"

            r = requests.get(
                url,
                params={'start': start},
                auth=HTTPBasicAuth(self.__username, self.__token),
                verify=self.__ssl_verify,
                timeout=self.__timeout
            )

            # Affiche le chunk (décodé/normalisé pour l'œil, offset en header)
            chunk = _sanitize_bytes(r.content)
            if chunk:
                print(chunk, end='', flush=True)

            # ⚠️ Offset correct = header Jenkins (taille EN OCTETS)
            next_start = int(r.headers.get('X-Text-Size', start))
            more = r.headers.get('X-More-Data') == 'true'
            if next_start < start:
                next_start = start
            start = next_start

            if not more:
                info = self.__connection.get_build_info(name, number)
                if not info.get('building', False):
                    return info.get('result') or 'UNKNOWN'
            time.sleep(0.5)
