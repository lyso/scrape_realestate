import mysql.connector

def db_connector(db):
    cnx = mysql.connector.connect(user='lyso',
                                  password='lyskey',
                                  host="localhost",
                                  database=db)
    return cnx