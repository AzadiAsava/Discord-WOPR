from abc import abstractmethod

class Sendable():
    @abstractmethod
    async def send(self, message:str) -> None:
        raise NotImplementedError("Not implemented")

