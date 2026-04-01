class Verifier:

    async def verify(self, result):

        if result is None:
            return False, "No result"

        text = str(result).lower()

        if "error" in text:
            return False, result

        if "failed" in text:
            return False, result

        return True, "OK"
