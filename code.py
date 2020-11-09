from random import randint
import mysql.connector
import random


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


def incert(cursor, query_heart_rythm, query_heart_oxygen, risk, usuario):

    for i in usuario:
        query = f'INSERT INTO Person(username) values("{i}");'
        cursor.execute(query)

    for i in range(len(query_heart_rythm)):
        queryGetName = f"SELECT * FROM Person WHERE username = 'user-{i % 4}'"
        cursor.execute(queryGetName)
        query = f'INSERT INTO Biometrics(ID_person, oxigen_level, Heart_rythm) values({cursor.fetchone()[0]}, "{query_heart_oxygen[i]}", "{query_heart_rythm[i]}");'
        cursor.execute(query)

    for i in risk:
        queryGetName = f"SELECT * FROM Person WHERE username = 'user-{i % 4}'"
        cursor.execute(queryGetName)
        query = (
            f"INSERT INTO State(ID_person, risk) values({cursor.fetchone()[0]}, {i});"
        )
        cursor.execute(query)


def printQuerry(cursor, table):
    query = f"SELECT * FROM {table};"
    cursor.execute(query)
    for result in cursor:
        print(result)


def main():
    query_heart_rythm = []
    query_heart_oxygen = []
    risk = []
    usuario = []
    for i in range(0, 5000):
        query_heart_rythm.append(randint(0, 1024))
        query_heart_oxygen.append(randint(0, 1024))
        risk.append(0)

    for i in range(1, 5):
        usuario.append(f"user-{i % 4}")

    cnx = makeConnection()
    cursor = cnx.cursor()
    incert(cursor, query_heart_rythm, query_heart_oxygen, risk, usuario)
    printQuerry(cursor, "Biometrics")
    cnx.commit()
    cnx.close()


main()
