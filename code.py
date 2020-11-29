from random import randint
import mysql.connector
import random
import numpy as np
import pandas as pd
import serial
import matplotlib.pyplot as plt
from datetime import datetime as dt
from pytz import timezone
import socket


import numpy as np

# 25 samples per second (in algorithm.h)
SAMPLE_FREQ = 25
# taking moving average of 4 samples when calculating HR
# in algorithm.h, "DONOT CHANGE" comment is attached
MA_SIZE = 4
# sampling frequency * 4 (in algorithm.h)
BUFFER_SIZE = 100


# this assumes ir_data and red_data as np.array
def calc_hr_and_spo2(ir_data, red_data):
    """
    By detecting  peaks of PPG cycle and corresponding AC/DC
    of red/infra-red signal, the an_ratio for the SPO2 is computed.
    """
    # get dc mean
    ir_mean = int(np.mean(ir_data))

    # remove DC mean and inver signal
    # this lets peak detecter detect valley
    x = -1 * (np.array(ir_data) - ir_mean)

    # 4 point moving average
    # x is np.array with int values, so automatically casted to int
    for i in range(x.shape[0] - MA_SIZE):
        x[i] = np.sum(x[i : i + MA_SIZE]) / MA_SIZE

    # calculate threshold
    n_th = int(np.mean(x))
    n_th = 30 if n_th < 30 else n_th  # min allowed
    n_th = 60 if n_th > 60 else n_th  # max allowed

    ir_valley_locs, n_peaks = find_peaks(x, BUFFER_SIZE, n_th, 4, 15)
    # print(ir_valley_locs[:n_peaks], ",", end="")
    peak_interval_sum = 0
    if n_peaks >= 2:
        for i in range(1, n_peaks):
            peak_interval_sum += ir_valley_locs[i] - ir_valley_locs[i - 1]
        peak_interval_sum = int(peak_interval_sum / (n_peaks - 1))
        hr = int(SAMPLE_FREQ * 60 / peak_interval_sum)
        hr_valid = True
    else:
        hr = -999  # unable to calculate because # of peaks are too small
        hr_valid = False

    # ---------spo2---------

    # find precise min near ir_valley_locs (???)
    exact_ir_valley_locs_count = n_peaks

    # find ir-red DC and ir-red AC for SPO2 calibration ratio
    # find AC/DC maximum of raw

    # FIXME: needed??
    for i in range(exact_ir_valley_locs_count):
        if ir_valley_locs[i] > BUFFER_SIZE:
            spo2 = -999  # do not use SPO2 since valley loc is out of range
            spo2_valid = False
            return hr, hr_valid, spo2, spo2_valid

    i_ratio_count = 0
    ratio = []

    # find max between two valley locations
    # and use ratio between AC component of Ir and Red DC component of Ir and Red for SpO2
    red_dc_max_index = -1
    ir_dc_max_index = -1
    for k in range(exact_ir_valley_locs_count - 1):
        red_dc_max = -16777216
        ir_dc_max = -16777216
        if ir_valley_locs[k + 1] - ir_valley_locs[k] > 3:
            for i in range(ir_valley_locs[k], ir_valley_locs[k + 1]):
                if ir_data[i] > ir_dc_max:
                    ir_dc_max = ir_data[i]
                    ir_dc_max_index = i
                if red_data[i] > red_dc_max:
                    red_dc_max = red_data[i]
                    red_dc_max_index = i

            red_ac = int(
                (red_data[ir_valley_locs[k + 1]] - red_data[ir_valley_locs[k]])
                * (red_dc_max_index - ir_valley_locs[k])
            )
            red_ac = red_data[ir_valley_locs[k]] + int(
                red_ac / (ir_valley_locs[k + 1] - ir_valley_locs[k])
            )
            red_ac = (
                red_data[red_dc_max_index] - red_ac
            )  # subtract linear DC components from raw

            ir_ac = int(
                (ir_data[ir_valley_locs[k + 1]] - ir_data[ir_valley_locs[k]])
                * (ir_dc_max_index - ir_valley_locs[k])
            )
            ir_ac = ir_data[ir_valley_locs[k]] + int(
                ir_ac / (ir_valley_locs[k + 1] - ir_valley_locs[k])
            )
            ir_ac = (
                ir_data[ir_dc_max_index] - ir_ac
            )  # subtract linear DC components from raw
            nume = red_ac * ir_dc_max
            denom = ir_ac * red_dc_max
            if (denom > 0 and i_ratio_count < 5) and nume != 0:
                # original cpp implementation uses overflow intentionally.
                # but at 64-bit OS, Pyhthon 3.X uses 64-bit int and nume*100/denom does not trigger overflow
                # so using bit operation ( &0xffffffff ) is needed
                ratio.append(int(((nume * 100) & 0xFFFFFFFF) / denom))
                i_ratio_count += 1

    # choose median value since PPG signal may vary from beat to beat
    ratio = sorted(ratio)  # sort to ascending order
    mid_index = int(i_ratio_count / 2)

    ratio_ave = 0
    if mid_index > 1:
        ratio_ave = int((ratio[mid_index - 1] + ratio[mid_index]) / 2)
    else:
        if len(ratio) != 0:
            ratio_ave = ratio[mid_index]

    # why 184?
    # print("ratio average: ", ratio_ave)
    if ratio_ave > 2 and ratio_ave < 184:
        # -45.060 * ratioAverage * ratioAverage / 10000 + 30.354 * ratioAverage / 100 + 94.845
        spo2 = (
            -45.060 * (ratio_ave ** 2) / 10000.0 + 30.054 * ratio_ave / 100.0 + 94.845
        )
        spo2_valid = True
    else:
        spo2 = -999
        spo2_valid = False

    return hr, hr_valid, spo2, spo2_valid


def find_peaks(x, size, min_height, min_dist, max_num):
    """
    Find at most MAX_NUM peaks above MIN_HEIGHT separated by at least MIN_DISTANCE
    """
    ir_valley_locs, n_peaks = find_peaks_above_min_height(x, size, min_height, max_num)
    ir_valley_locs, n_peaks = remove_close_peaks(n_peaks, ir_valley_locs, x, min_dist)

    n_peaks = min([n_peaks, max_num])

    return ir_valley_locs, n_peaks


def find_peaks_above_min_height(x, size, min_height, max_num):
    """
    Find all peaks above MIN_HEIGHT
    """

    i = 0
    n_peaks = 0
    ir_valley_locs = []  # [0 for i in range(max_num)]
    while i < size - 1:
        if (
            x[i] > min_height and x[i] > x[i - 1]
        ):  # find the left edge of potential peaks
            n_width = 1
            # original condition i+n_width < size may cause IndexError
            # so I changed the condition to i+n_width < size - 1
            while i + n_width < size - 1 and x[i] == x[i + n_width]:  # find flat peaks
                n_width += 1
            if (
                x[i] > x[i + n_width] and n_peaks < max_num
            ):  # find the right edge of peaks
                # ir_valley_locs[n_peaks] = i
                ir_valley_locs.append(i)
                n_peaks += 1  # original uses post increment
                i += n_width + 1
            else:
                i += n_width
        else:
            i += 1

    return ir_valley_locs, n_peaks


def remove_close_peaks(n_peaks, ir_valley_locs, x, min_dist):
    """
    Remove peaks separated by less than MIN_DISTANCE
    """

    # should be equal to maxim_sort_indices_descend
    # order peaks from large to small
    # should ignore index:0
    sorted_indices = sorted(ir_valley_locs, key=lambda i: x[i])
    sorted_indices.reverse()

    # this "for" loop expression does not check finish condition
    # for i in range(-1, n_peaks):
    i = -1
    while i < n_peaks:
        old_n_peaks = n_peaks
        n_peaks = i + 1
        # this "for" loop expression does not check finish condition
        # for j in (i + 1, old_n_peaks):
        j = i + 1
        while j < old_n_peaks:
            n_dist = (
                (sorted_indices[j] - sorted_indices[i])
                if i != -1
                else (sorted_indices[j] + 1)
            )  # lag-zero peak of autocorr is at index -1
            if n_dist > min_dist or n_dist < -1 * min_dist:
                sorted_indices[n_peaks] = sorted_indices[j]
                n_peaks += 1  # original uses post increment
            j += 1
        i += 1

    sorted_indices[:n_peaks] = sorted(sorted_indices[:n_peaks])

    return sorted_indices, n_peaks


def makeConnection():
    try:
        cnx = mysql.connector.connect(
            user="root", password="42admin420", host="127.0.0.1", database="healthData"
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


def dataBaseIncertion(hr, ox, user):
    cnx = makeConnection()
    cursor = cnx.cursor()

    queryGetName = f"SELECT * FROM Person WHERE username = 'user-{user}'"
    cursor.execute(queryGetName)
    idUser = cursor.fetchone()
    if idUser == None:
        print("1 ", idUser)
        query = f'INSERT INTO Person(username) values("user-{user}");'
        cursor.execute(query)

    incert(cursor, hr, ox, 0, user)
    cnx.commit()
    cnx.close()


def printQuerry(cursor, table):
    query = f"SELECT * FROM {table};"
    cursor.execute(query)
    for result in cursor:
        print(result)


def expMovingAverages(ir, red, alfa=0.9):
    listaSuavisadaRed = []
    listaSuavisadaRed.append(red[0])
    for i in red:
        listaSuavisadaRed.append(alfa * i + (1 - alfa) * listaSuavisadaRed[-1])

    listaSuavisadaIr = []
    listaSuavisadaIr.append(ir[-1])
    for i in ir:
        listaSuavisadaIr.append(alfa * i + (1 - alfa) * listaSuavisadaIr[-1])

    return (listaSuavisadaIr, listaSuavisadaRed)


def simpleMovingAverages(hr, ox, k=3):
    df = pd.DataFrame(list(zip(hr, ox)), columns=["ir", "red"])
    df = df.rolling(k, min_periods=1).mean()

    return df


def dataPlot(data, time):
    hr, ox = data
    hr.pop()
    ox.pop()
    plt.plot(time, hr, label="hr", color="r")
    plt.plot(time, ox, label="ox", color="b")
    plt.show()


def dataProcesing(irList, redList, time, user):
    mesage = "Puede que estes en riesgo"
    tupMAS = simpleMovingAverages(redList, irList).values.tolist()
    tupMAE = expMovingAverages(redList, irList, 0.9)
    # dataBaseIncertion(*tupMAE)
    # dataPlot(tupMAS, time)

    ir1 = irList[0:100]
    ir2 = irList[100:200]
    ir3 = irList[200:300]
    ir4 = irList[300:400]
    ir5 = irList[400:500]
    ir6 = irList[500:600]
    ir7 = irList[600:700]
    ir8 = irList[700:800]
    ir9 = irList[800:900]
    ir10 = irList[900:1000]

    red1 = redList[0:100]
    red2 = redList[100:200]
    red3 = redList[200:300]
    red4 = redList[300:400]
    red5 = redList[400:500]
    red6 = redList[500:600]
    red7 = redList[600:700]
    red8 = redList[700:800]
    red9 = redList[800:900]
    red10 = redList[900:1000]

    hr1, hr_valid1, spo21, spo2_valid1 = calc_hr_and_spo2(ir1, red1)
    hr2, hr_valid2, spo22, spo2_valid2 = calc_hr_and_spo2(ir2, red2)
    hr3, hr_valid3, spo23, spo2_valid3 = calc_hr_and_spo2(ir3, red3)
    hr4, hr_valid4, spo24, spo2_valid4 = calc_hr_and_spo2(ir4, red4)
    hr5, hr_valid5, spo25, spo2_valid5 = calc_hr_and_spo2(ir5, red5)
    hr6, hr_valid6, spo26, spo2_valid6 = calc_hr_and_spo2(ir6, red6)
    hr7, hr_valid7, spo27, spo2_valid7 = calc_hr_and_spo2(ir7, red7)
    hr8, hr_valid8, spo28, spo2_valid8 = calc_hr_and_spo2(ir8, red8)
    hr9, hr_valid9, spo29, spo2_valid9 = calc_hr_and_spo2(ir9, red9)
    hr10, hr_valid10, spo210, spo2_valid10 = calc_hr_and_spo2(ir10, red10)

    hr = 0
    ox = 0
    if hr_valid1 != False and spo21 > 80:
        hr = hr1
        ox = spo21
    if hr_valid2 != False and spo22 > 80 and spo22 > ox:
        hr = hr2
        ox = spo22
    if hr_valid3 != False and spo23 > 80 and spo23 > ox:
        hr = hr3
        ox = spo23
    if hr_valid4 != False and spo24 > 80 and spo24 > ox:
        hr = hr4
        ox = spo24
    if hr_valid5 != False and spo25 > 80 and spo25 > ox:
        hr = hr5
        ox = spo25
    if hr_valid6 != False and spo26 > 80 and spo26 > ox:
        hr = hr6
        ox = spo26
    if hr_valid7 != False and spo27 > 80 and spo27 > ox:
        hr = hr7
        ox = spo27
    if hr_valid8 != False and spo28 > 80 and spo28 > ox:
        hr = hr8
        ox = spo28
    if hr_valid9 != False and spo29 > 80 and spo29 > ox:
        hr = hr9
        ox = spo29
    if hr_valid10 != False and spo210 > 80 and spo210 > ox:
        hr = hr10
        ox = spo210

    if hr == 0:
        hr = -1
        ox = -1
    else:
        dataBaseIncertion(hr, ox, user)

    if ox > 93:
        mesage = "Estas saludable"
    print(f"hr: {hr}, spo2: {ox}")
    return mesage
    # dataPlot(tupMAE, time)


def sendResult(s, result):
    s.connect(("192.168.1.119", 1337))
    result += "\r\n\r\n"
    result = result.encode("utf-8")
    # dataFromClient = s.recv(1024)
    while 1:
        # dataFromClient = s.recv(1024)
        print("send")
        s.send(result)


def reciveData():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.bind(("0.0.0.0", 1337))
    result = "Error"
    irList = []
    redList = []
    time = []
    usert = 0
    # ser = serial.Serial("/dev/cu.usbmodem14101", 9600)
    recive = True
    while recive:
        try:
            lineBytes = lineBytes = s.recv(1024)
            line = lineBytes.decode("ascii")
            line = line.rstrip()
            partes = line.split(";")
            ir = int(partes[0].split(":")[1])
            red = int(partes[1].split(":")[1])
            milis = int(partes[2].split(":")[1])
            user = int(partes[3].split(":")[1])
            cont = int(partes[4].split(":")[1])
            irList.append(ir)
            redList.append(red)
            time.append(milis)
            # print(partes)
            print(f"ir: {ir}, red: {red}, user: {user}, size: {cont}")
            if usert != user:
                usert = user
                irList.clear()
                redList.clear()
                time.clear()
            if cont >= 1000:
                recive = True
                result = dataProcesing(irList, redList, time, user)
                irList.clear()
                redList.clear()
                time.clear()
                break
        except Exception as e:
            print(e)
            continue
    sendResult(s, result)


def main():
    reciveData()


main()
