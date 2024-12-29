# Copyright (c) 2023 Cisco Systems, Inc. and its affiliates All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from concurrent import futures
import random
import datetime
import os
import grpc
from accounts_pb2 import *
import accounts_pb2_grpc
import logging
from dotmap import DotMap
from pymongo.mongo_client import MongoClient
from flask import Flask, request, jsonify
import requests

# set logging to debug
logging.basicConfig(level=logging.DEBUG)
# Suppress pymongo DEBUG logs
logging.getLogger('pymongo').setLevel(logging.WARNING)

from dotenv import load_dotenv
load_dotenv()

# db_host = os.getenv("DATABASE_HOST", "localhost")
db_url = os.getenv("DB_URL")
if db_url is None:
    raise Exception("DB_URL environment variable is not set")


# protocol = os.getenv('SERVICE_PROTOCOL')
protocol = os.getenv('SERVICE_PROTOCOL', 'http')
if protocol is None:
    raise Exception("SERVICE_PROTOCOL environment variable is not set")

protocol = protocol.lower()
logging.debug(f"microservice protocol: {protocol}")


uri = db_url

# Initialize MongoDB client
client = MongoClient(uri)
db = client["bank"]
collection = db["accounts"]

app = Flask(__name__)
accounts_generic = None  # Will be initialized later

class AccountsGeneric:
    def getAccountDetails(self, request):
        logging.debug("Get Account Details called")
        account = collection.find_one({"account_number": request.account_number})

        if account:
            return {
                'account_number': account["account_number"],
                'name': account["name"],
                'balance': account["balance"],
                'currency': account["currency"],
                'email_id': account["email_id"],
                'account_type': account["account_type"]
            }

        return {}

    # Method to create a new account
    def createAccount(self, request):
        logging.debug("Create Account called")
        # Check if the account with email and account type already exists
        count = collection.count_documents(
            {"email_id": request.email_id, "account_type": request.account_type}
        )

        logging.debug(f"Count: {count}")

        if count > 0:
            logging.debug("Account already exists")
            return False  # Account creation failed

        account = {
            "email_id": request.email_id,
            "account_type": request.account_type,
            "address": request.address,
            "govt_id_number": request.govt_id_number,
            "government_id_type": request.government_id_type,
            "name": request.name,
            "balance": 100,  # Initial balance
            "currency": "USD",
            "account_number": f"IBAN{random.randint(1000000000000000, 9999999999999999)}",
            "created_at": datetime.datetime.now()
        }

        # Insert the account into the database
        collection.insert_one(account)
        logging.debug(f"Account created with account_number: {account['account_number']}")
        return True  # Account creation successful

    # Method to get accounts based on email_id and optionally account_number
    def getAccounts(self, request):
        email_id = request.email_id
        account_number = getattr(request, 'account_number', None)  # Optional

        query = {"email_id": email_id}

        if account_number:
            query["account_number"] = account_number

        accounts = collection.find(query)
        account_list = []
        for account in accounts:
            acc = {
                k: v
                for k, v in account.items()
                if k in [
                    "account_number",
                    "email_id",
                    "account_type",
                    "address",
                    "govt_id_number",
                    "government_id_type",
                    "name",
                    "balance",
                    "currency",
                ]
            }
            account_list.append(acc)

        return account_list

    def updateBalance(self, request):
        logging.debug("Update Balance called")
        account_number = request.account_number
        new_balance = request.new_balance

        if new_balance < 0:
            logging.debug("Invalid balance value")
            return False  # Invalid balance

        result = collection.update_one(
            {"account_number": account_number},
            {"$set": {"balance": new_balance}}
        )

        if result.matched_count == 0:
            logging.debug("Account not found")
            return False  # Account not found

        logging.debug(f"Account {account_number} balance updated to {new_balance}")
        return True  # Update successful

class AccountDetailsService(accounts_pb2_grpc.AccountDetailsServiceServicer):
    def __init__(self):
        self.accounts = AccountsGeneric()

    def getAccountDetails(self, request, context):
        logging.debug("gRPC Get Account Details called")
        account = self.accounts.getAccountDetails(request)

        if len(account) > 0:
            return AccountDetail(
                account_number=account["account_number"],
                name=account["name"],
                balance=account["balance"],
                currency=account["currency"],
                email_id=account["email_id"],
                account_type=account["account_type"]
            )
        return AccountDetail()

    def createAccount(self, request, context):
        logging.debug("gRPC Create Account called")
        result = self.accounts.createAccount(request)
        return CreateAccountResponse(result=result)

    def getAccounts(self, request, context):
        logging.debug("gRPC Get Accounts called")
        accounts = self.accounts.getAccounts(request)
        account_list = []
        for account in accounts:
            account_list.append(
                Account(
                    account_number=account["account_number"],
                    email_id=account["email_id"],
                    account_type=account["account_type"],
                    address=account["address"],
                    govt_id_number=account["govt_id_number"],
                    government_id_type=account["government_id_type"],
                    name=account["name"],
                    balance=account["balance"],
                    currency=account["currency"],
                )
            )
        return GetAccountsResponse(accounts=account_list)

    def updateBalance(self, request, context):
        logging.debug("gRPC Update Balance called")
        success = self.accounts.updateBalance(request)
        return UpdateBalanceResponse(success=success)

accounts_generic = AccountsGeneric()

# Flask Routes
@app.route("/account-detail", methods=["POST"])
def getAccountDetails():
    data = request.json
    data = DotMap(data)
    account = accounts_generic.getAccountDetails(data)
    return jsonify(account)

@app.route("/create-account", methods=["POST"])
def createAccount():
    data = request.json
    data = DotMap(data)
    result = accounts_generic.createAccount(data)
    return jsonify({"success": result})

@app.route("/get-all-accounts", methods=["POST"])
def getAccounts():
    data = request.json
    data = DotMap(data)
    accounts = accounts_generic.getAccounts(data)
    return jsonify(accounts)

@app.route("/get-account-by-email", methods=["POST"])
def getAccountByEmail():
    logging.debug("Get Account By Email API called")
    data = request.json
    data = DotMap(data)
    email_id = data.email_id
    account_type = getattr(data, 'account_type', None)  # Optional

    query = {"email_id": email_id}
    if account_type:
        query["account_type"] = account_type

    account = collection.find_one(query)
    if account:
        return jsonify({
            'account_number': account["account_number"],
            'name': account["name"],
            'balance': account["balance"],
            'currency': account["currency"],
            'email_id': account["email_id"],
            'account_type': account["account_type"]
        })
    return jsonify({}), 404

# Note: this route is used only by loan service to update the balance
@app.route("/update-balance", methods=["POST"])
def updateBalance():
    data = request.json
    data = DotMap(data)
    account_number = data.account_number
    new_balance = data.new_balance

    # Input validation
    if not isinstance(new_balance, (int, float)) or new_balance < 0:
        logging.debug("Invalid new_balance value received")
        return jsonify({"success": False, "message": "Invalid balance value."}), 400

    # Create a mock request object for the AccountsGeneric method
    class UpdateBalanceRequest:
        def __init__(self, account_number, new_balance):
            self.account_number = account_number
            self.new_balance = new_balance

    request_obj = UpdateBalanceRequest(account_number, new_balance)
    success = accounts_generic.updateBalance(request_obj)

    if success:
        return jsonify({"success": True, "message": "Balance updated successfully."})
    else:
        return jsonify({"success": False, "message": "Account not found or invalid balance."}), 404

def serverFlask(port):
    logging.debug(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0', port=port, debug=True)

def serverGRPC(port):
    # recommendations_host = os.getenv("RECOMMENDATIONS_HOST", "localhost")
    logging.debug(f"Starting gRPC server on port {port}")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    accounts_pb2_grpc.add_AccountDetailsServiceServicer_to_server(
        AccountDetailsService(), server
    )
    server.add_insecure_port(f"[::]:{port}")
    # server.add_insecure_port(f"{recommendations_host}:50051")
    # print server ip and port
    logging.debug(f"Server started at port {port}")
    # print IP
    server.start()
    server.wait_for_termination()

if __name__ == "__main__":
    port = 50051
    # serverGRPC(port)
    if protocol == "grpc":
        serverGRPC(port)
    else:
        serverFlask(port)
