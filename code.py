from random import randint
import mysql.connector
import random
from datetime import datetime as dt
from pytz import timezone


def makeConnection():
    try:
        cnx = mysql.connector.connect(
            user="root", password="42admin", host="127.0.0.1", database="healthData"
        )
        return cnx

    except mysql.connector.Error as err:

        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            print("Something is wrong with your user name or password")
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            print("Database does not exist")
        else:
            print(err)


def addUser(cursor, usuario):
    query = f'INSERT INTO Person(username) values("{usuario}");'
    cursor.execute(query)


def incert(cursor, query_heart_rythm, query_heart_oxygen, risk, usuario):
    zonaHoraria = timezone("America/Mexico_City")
    fechaHora = dt.now(zonaHoraria)
    fechaHoraFormato = fechaHora.strftime("%Y-%m-%d %H:%M:%S")
    queryGetName = f"SELECT * FROM Person WHERE username = 'user-{usuario}'"
    cursor.execute(queryGetName)
    idUser = cursor.fetchone()[0]

    query = f'INSERT INTO Biometrics(ID_person, oxigen_level, Heart_rythm, date) values({idUser}, "{query_heart_oxygen}", "{query_heart_rythm}", "{fechaHoraFormato}");'
    cursor.execute(query)

    query = f"INSERT INTO State(ID_person, risk, date) values({idUser}, {risk}, '{fechaHoraFormato}');"
    cursor.execute(query)


def printQuerry(cursor, table):
    query = f"SELECT * FROM {table};"
    cursor.execute(query)
    for result in cursor:
        print(result)


def main():
    cnx = makeConnection()
    cursor = cnx.cursor()
    nunOfUsers = 0
    for i in range(1, 5):
        addUser(cursor, f"user-{i % 4}")
        nunOfUsers += 1

    for i in range(0, 5000):
        incert(cursor, randint(0, 1024), randint(0, 1024), 0, i % nunOfUsers)

    cnx.commit()
    cnx.close()


main()
