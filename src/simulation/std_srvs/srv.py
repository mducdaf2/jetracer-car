# std_srvs/srv.py mock file
class SetBool:
    pass

class SetBoolResponse:
    def __init__(self, success=False, message=""):
        self.success = success
        self.message = message
