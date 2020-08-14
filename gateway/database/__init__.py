# !/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Mar 12 15:37:47 2019

@author: python
"""
import sqlalchemy as sa

# Define a version number for the database generated by these writers
# Increment this version number any time a change is made to the schema of the
# asset database
# NOTE: When upgrading this remember to add a downgrade in:
# .asset_db_migrations
ASSET_DB_VERSION = 8
SQLITE_MAX_VARIABLE_NUMBER = 999

# A frozenset of the names of all tables in the asset db
# NOTE: When modifying this schema, update the ASSET_DB_VERSION value
config = {
    "user": 'root',
    "password": 'macpython',
    "host": 'localhost',
    "port": '3306',
    'database': 'test01'
}

# engine_path = 'mysql+pymysql://root:macpython@localhost:3306/test01'
engine_path = 'mysql+pymysql://{user}:{password}@{host}:{port}/{database}'.format(user=config['user'],
                                                                                  password=config['password'],
                                                                                  host=config['host'],
                                                                                  port=config['port'],
                                                                                  database=config['database'],)

engine = sa.create_engine(engine_path)

metadata = sa.MetaData(bind=engine)


