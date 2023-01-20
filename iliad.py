import asyncio
import parsel
import asyncio
from aiohttp.client_exceptions import ClientConnectionError
import aiohttp
from dotenv import load_dotenv
from os import environ as env

# TODO remove dependencies textwrap e configparser
# TODO generate requirements

################################################################## UTILITIES
class Serializable:
    def as_dict(self, obj = None):
        ret = {}
        if obj != None:
            read = obj.__dict__
        else:
            read = self.__dict__

        for key in read:
            value = read[key]
            if "data." in str(type(value)):
                ret[key] = self.as_dict(obj=value)
            else:
                ret[key] = value
        return ret

class Settable:
    def __setitem__(self,k,v):
        setattr(self,k,v)
        
    def __getitem__(self,k):
        return getattr(self, k)
    
    def set(self,obj: object):
        if obj == None:
            return
        
        for key in obj:
            self[key] = obj[key]

class LoginFailedException(Exception):
    def __init__(self, *args: object) -> None:
        super().__init__(*args)

################################################################## ACTUAL DATA SCRAPING
class Usage(Serializable, Settable):
    
    calls: str = ""
    cost: str = ""
    sms: int | None = None
    sms_cost: str = ""
    mms: int | None = None
    mms_cost: str = ""
    data: str = ""
    data_limit: str = ""
    data_cost: str = ""
    data_extra: str = ""

    def __init__(self, root: parsel.Selector) -> "Usage":
        
        CONSO_TEXT = ".conso__text"

        self.calls = root.css(CONSO_TEXT).re_first('Chiamate: <span class="red">(.*)</span>')
        self.calls_cost = root.css(CONSO_TEXT).re_first('Consumi voce: <span class="red">(.*)</span>')
        self.sms = root.css(CONSO_TEXT).re_first('<span class="red">(.*) SMS</span>')
        self.sms_cost = root.css(CONSO_TEXT).re_first('SMS extra: <span class="red">(.*)</span>')
        self.mms = root.css(CONSO_TEXT).re_first('<span class="red">(.*) MMS<br></span>')
        self.mms_cost = root.css(CONSO_TEXT).re_first('Consumi MMS: <span class="red">(.*)</span>')
        self.data = root.css(CONSO_TEXT).re_first('<span class="red">(.*)</span> / .*<br>')
        self.data_limit = root.css(CONSO_TEXT).re_first('<span class="red">.*</span> / (.*)<br>')
        self.data_cost = root.css(CONSO_TEXT).re_first('Consumi Dati: <span class="red">(.*)</span>')
        self.data_extra = root.css(CONSO_TEXT).re_first(
            r'Consumi Dati: <span class="red">.*</span><br>\s+<span class="red">(.*)</span>'
        )

    # TODO is empty
    def isEmpty(self):
        pass

class UserData(Serializable, Settable):

    user : str = ""
    password : str = ""
    name : str = ""
    id : int | None = None
    number : int | None = None
    local : Usage | None = None
    roamin : Usage | None = None


    def __init__(self, user: str, pwd: str) -> None:
        self.user = user
        self.password = pwd

    async def get(self):

        html = ""
    
        async with aiohttp.ClientSession() as session:
            url = "https://www.iliad.it/account/"
            data = {"login-ident": self.user, "login-pwd": self.password}
            # cookies = await asyncio.gather(login(session, url, data)) #type: ignore
            
            async with session.post(url, data=data) as resp:
                html = await resp.text()

        root = parsel.Selector(text=html)
        info_parent = root.css(".current-user__infos")

        # Test if i reached the page or i'm into login screen
        if "<span>Accedi</span>" in root.get():
            raise LoginFailedException("Not logged in, sorry")

        else:
            info = info_parent

            self.name = info.css(".bold::text").get()
            self.id = info.css(".smaller").re_first(r"ID utente: (\d+)")
            self.number = info.css(".smaller").re_first("Numero: ([0-9 ]+)")

            self.local = Usage(root.css(".conso-local"))
            self.roaming = Usage(root.css(".conso-roaming"))

if __name__ == "__main__":

    load_dotenv()

    cp = {
        "iliad":{
            "user":env.get("USER"),
            "pass":env.get("PASS")
        }
    }
    print(cp)

    loop = asyncio.get_event_loop()
    try:
        user = UserData(cp["iliad"]["user"], cp["iliad"]["pass"])
        
        loop.run_until_complete(user.get())

        print(user.as_dict())

    except ClientConnectionError as ex:
        print("Connection error: "+str(ex))
    except LoginFailedException as ex:
        print("Login error: "+str(ex))
    except Exception as ex:
        print("Exception: "+str(ex))
