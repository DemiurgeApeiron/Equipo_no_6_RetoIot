from random import randint
import mysql.connector
import random
import numpy as np
import pandas as pd
import serial
import matplotlib.pyplot as plt
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


def expMovingAverages(hr, ox, alfa=0.9):
    listaSuavisadaHr = []
    listaSuavisadaHr.append(hr[-1])
    for i in hr:
        listaSuavisadaHr.append(alfa * i + (1 - alfa) * listaSuavisadaHr[-1])

    listaSuavisadaOx = []
    listaSuavisadaOx.append(ox[-1])
    for i in ox:
        listaSuavisadaOx.append(alfa * i + (1 - alfa) * listaSuavisadaOx[-1])

    return (listaSuavisadaHr, listaSuavisadaOx)


def simpleMovingAverages(hr, ox, k=3):
    df = pd.DataFrame(list(zip(hr, ox)), columns=["ir", "red"])
    df = df.rolling(k, min_periods=1).mean()

    return df


def dataBaseIncertion(hr, ox):
    cnx = makeConnection()
    cursor = cnx.cursor()
    nunOfUsers = 0
    for i in range(1, 5):
        addUser(cursor, f"user-{i % 4}")
        nunOfUsers += 1

    for i in range(0, 5000):
        incert(cursor, randint(0, 1024), randint(0, 1024), 0, i % nunOfUsers)

    # cnx.commit()
    cnx.close()


def dataPlot(data, time):
    hr, ox = data
    hr.pop()
    ox.pop()
    plt.plot(time, hr, label="h1", color="r")
    plt.plot(time, ox, label="ox", color="b")
    plt.show()


def dataProcesing(irList, redList, time):
    tupMAS = simpleMovingAverages(redList, irList).values.tolist()
    tupMAE = expMovingAverages(redList, irList, 0.3)
    # dataBaseIncertion(*tupMAE)
    # dataPlot(tupMAS, time)
    dataPlot(tupMAE, time)


def main():

    irList = []
    redList = []
    time = []
    ser = serial.Serial("/dev/cu.usbmodem14101", 115200)
    while 1:
        try:
            lineBytes = ser.readline()
            line = lineBytes.decode("ascii")
            line = line.rstrip()
            partes = line.split(";")
            ir = int(partes[0].split(":")[1])
            red = int(partes[1].split(":")[1])
            milis = int(partes[2].split(":")[1])
            irList.append(ir)
            redList.append(red)
            time.append(milis)
            print(ir)
            if len(irList) >= 5000:
                dataProcesing(irList, redList, time)
                irList.clear()
                redList.clear()
                time.clear()

        except Exception as e:
            print(e)
            continue


main()
