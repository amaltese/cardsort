import secrets

class CompletionService:
    @staticmethod
    def generate_completion_code() -> str:
        part1 = secrets.token_hex(2).upper()
        part2 = secrets.token_hex(2).upper()
        return f"{part1}-{part2}"