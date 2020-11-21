queryGetName = f"SELECT * FROM Person WHERE username = 'user-{usuario}'"
    cursor.execute(queryGetName)
    idUser = cursor.fetchone()[0]