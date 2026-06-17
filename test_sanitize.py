import re

def sanitize_token_old(text: str) -> str:
    if "echo password=" in text:
        text = re.sub(r"(echo password=).*", r"\1***", text)
    return text

def sanitize_token_new(text: str) -> str:
    if "echo password=" in text:
        text = re.sub(r'(echo password=)"((?:\\.|[^"\\])*)"', r'\1"***"', text)
        text = re.sub(r"(echo password=)'((?:\\.|[^'\\])*)'", r"\1'***'", text)
        text = re.sub(r'(echo password=)(?![\'"])([^;\r\n]+)', r'\1***', text)

    if "ghp_" in text:
        text = re.sub(r"ghp_[a-zA-Z0-9]{36}", "***", text)
    if "github_pat_" in text:
        text = re.sub(r"github_pat_[a-zA-Z0-9_]{82}", "***", text)

    return text

cmd = "credential.helper=!f() { echo username=token; echo password='SECRET_TOKEN'; }; f"
print("OLD:", sanitize_token_old(cmd))
print("NEW:", sanitize_token_new(cmd))

cmd_double = "echo password=\"SECRET\" ; ls"
print("OLD:", sanitize_token_old(cmd_double))
print("NEW:", sanitize_token_new(cmd_double))

cmd_unquoted = "echo password=SECRET; ls"
print("OLD:", sanitize_token_old(cmd_unquoted))
print("NEW:", sanitize_token_new(cmd_unquoted))
