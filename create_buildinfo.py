import datetime
date_today = datetime.date.today().strftime("%Y.%m.%d")
with open("src/pycmd/buildinfo.py", "w") as f:
    f.write(f'build_date = "{date_today}"')
print(date_today)
