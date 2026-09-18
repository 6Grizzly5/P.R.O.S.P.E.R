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

from app.commands.apps import (open_application,
    close_application)


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
            "find": self.find
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
        info = get_system_info()

        return {
            "success": True,
            "type": "system",
            "data": info
        }

    def time(self, argument=""):
        current_time = get_current_time()

        return {
            "success": True,
            "type": "time",
            "data": current_time
        }

    def pwd(self, argument=""):
        directory = get_current_directory()

        return {
            "success": True,
            "type": "pwd",
            "data": directory
        }

    def open(self, argument):
        result = open_application(argument)

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
        
    def close(self, argument):
        result = close_application(argument)

        return {
            "success": True,
            "type": "message",
            "data": result
        }


    def find(self, argument):
        results = find_file(argument)

        return {
            "success": True,
            "type": "find",
            "data": results
        }