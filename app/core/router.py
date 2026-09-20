from app.commands.system import (
    get_system_info,
    get_current_time,
    get_current_directory
)

from app.commands.files import (
    create_folder,
    delete_folder,
    list_folder,
    find_file
)

from app.commands.apps import (
    open_application,
    close_application
)

from app.memory.memory import (
    remember,
    forget,
    get_memory,
    get_history
)


class CommandRouter:

    def __init__(self):
        self.commands = {
            "system": self.system,
            "time": self.time,
            "pwd": self.pwd,
            "open": self.open,
            "close": self.close,
            "create": self.create,
            "delete": self.delete,
            "list": self.list,
            "find": self.find,
            "remember": self.remember,
            "forget": self.forget,
            "memory": self.memory,
            "history": self.history
        }

    def execute(self, action, argument=""):

        action = action.lower()

        if action not in self.commands:

            return {
                "success": False,
                "message": f"Commande inconnue : '{action}'."
            }

        return self.commands[action](argument)

    def system(self, argument=""):

        return {
            "success": True,
            "type": "system",
            "data": get_system_info()
        }

    def time(self, argument=""):

        return {
            "success": True,
            "type": "time",
            "data": get_current_time()
        }

    def pwd(self, argument=""):

        return {
            "success": True,
            "type": "pwd",
            "data": get_current_directory()
        }

    def open(self, argument):

        result = open_application(argument)

        return {
            "success": True,
            "type": "message",
            "data": result
        }

    def close(self, argument):

        result = close_application(argument)

        return {
            "success": True,
            "type": "message",
            "data": result
        }

    def create(self, argument):

        result = create_folder(argument)

        return {
            "success": True,
            "type": "message",
            "data": result
        }

    def delete(self, argument):

        result = delete_folder(argument)

        return {
            "success": True,
            "type": "message",
            "data": result
        }

    def list(self, argument):

        folder = argument if argument else "."

        result = list_folder(folder)

        return {
            "success": True,
            "type": "list",
            "data": result
        }

    def find(self, argument):

        result = find_file(argument)

        return {
            "success": True,
            "type": "find",
            "data": result
        }

    def remember(self, argument):

        if not argument or " " not in argument:

            return {
                "success": False,
                "message": "Utilisation : remember <clé> <valeur>"
            }

        key, value = argument.split(" ", 1)

        result = remember(key, value)

        return {
            "success": True,
            "type": "message",
            "data": result
        }

    def forget(self, argument):

        result = forget(argument)

        return {
            "success": True,
            "type": "message",
            "data": result
        }

    def memory(self, argument):

        result = get_memory()

        return {
            "success": True,
            "type": "memory",
            "data": result
        }

    def history(self, argument):

        result = get_history()

        return {
            "success": True,
            "type": "history",
            "data": result
        }