# Copyright (c) 2023 Cisco Systems, Inc. and its affiliates All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from concurrent import futures
import random
import datetime
import os
import grpc
import requests

import logging
from flask import Flask, request, jsonify
# set logging to debug
logging.basicConfig(level=logging.DEBUG)
# Suppress pymongo DEBUG logs
logging.getLogger('pymongo').setLevel(logging.WARNING)


from loan_pb2 import *
import loan_pb2_grpc

from pymongo.mongo_client import MongoClient

from dotenv import load_dotenv
load_dotenv()


# db_host = os.getenv("DATABASE_HOST", "localhost")
db_url = os.getenv("DB_URL")
if db_url is None:
    raise Exception("DB_URL environment variable is not set")

uri = db_url

protocol = os.getenv('SERVICE_PROTOCOL', 'http')
if protocol is None:
    raise Exception("SERVICE_PROTOCOL environment variable is not set")

protocol = protocol.lower()

logging.debug(f"microservice protocol: {protocol}")



client = MongoClient(uri)
db = client["bank"]
collection_loans = db["loans"]

ACCOUNTS_SERVICE_URL = os.getenv("ACCOUNTS_SERVICE_URL")
if not ACCOUNTS_SERVICE_URL:
    raise Exception("ACCOUNTS_SERVICE_URL environment variable is not set")

class LoanGeneric:
    def ProcessLoanRequest(self, request_data):
        name = request_data["name"]
        email = request_data["email"]
        account_type = request_data["account_type"]
        account_number = request_data["account_number"]
        govt_id_type = request_data["govt_id_type"]
        govt_id_number = request_data["govt_id_number"]
        loan_type = request_data["loan_type"]
        loan_amount = float(request_data["loan_amount"])
        interest_rate = float(request_data["interest_rate"])
        time_period = request_data["time_period"]
        user_account = self.__getAccount(account_number)
        
        try:
            # Prepare payload for Accounts API
            payload = {
            "email_id": email,
            "account_number": account_number
            }
            logging.debug(f"Sending POST request to Accounts Service with payload: {payload}")
    
            # Send POST request to Accounts API
            response = requests.post(f"{ACCOUNTS_SERVICE_URL}/get-all-accounts", json=payload, timeout=5)
    
            # Check HTTP status code
            if response.status_code != 200:
                logging.error(f"Error in request to Accounts Service: {response.status_code} - {response.text}")
                return {"approved": False, "message": "Error communicating with Accounts Service."}
    
            # Process response
            accounts = response.json()
            count = len(accounts)
            logging.debug(f"Number of accounts found: {count}")
        except requests.exceptions.RequestException as e:
            logging.error(f"Exception during communication with Accounts Service: {e}")
            return {"approved": False, "message": "Error communicating with Accounts Service."}
        except ValueError as e:
            logging.error(f"Error parsing JSON response: {e}")
            return {"approved": False, "message": "Invalid response from Accounts Service."}


        logging.debug(f"user account only based on account number search : {user_account}")
        logging.debug(f"Count wether the email and account exist or not : {count}")
        if count == 0:
            return {"approved": False, "message": "Email or Account number not found."}
        result = self.__approveLoan(user_account, loan_amount)
        logging.debug(f"Result {result}")
        message = "Loan Approved" if result else "Loan Rejected"
        
        # insert loan request into db
        loan_request = {
            "name": name,
            "email": email,
            "account_type": account_type,
            "account_number": account_number,
            "govt_id_type": govt_id_type,
            "govt_id_number": govt_id_number,
            "loan_type": loan_type,
            "loan_amount": loan_amount,
            "interest_rate": interest_rate,
            "time_period": time_period,
            "status": "Declined",
            "timestamp": datetime.datetime.now(),
        }
        loan_request["status"] = "Approved" if result else "Declined"

        collection_loans.insert_one(loan_request)

        response = {"approved": result, "message": message}
        logging.debug(f"Account: {account_number}")
        logging.debug(f"Response: {response}")
        return response

    def getLoanHistory(self, request_data):
        email = request_data["email"]
        loans = collection_loans.find({"email": email})
        loan_history = []

        for l in loans:
            loan_history.append(
                {
                    "name": l["name"],
                    "email": l["email"],
                    "account_type": l["account_type"],
                    "account_number": l["account_number"],
                    "govt_id_type": l["govt_id_type"],
                    "govt_id_number": l["govt_id_number"],
                    "loan_type": l["loan_type"],
                    "loan_amount": l["loan_amount"],
                    "interest_rate": l["interest_rate"],
                    "time_period": l["time_period"],
                    "status": l["status"],
                    "timestamp": f"{l['timestamp']}",
                }
            )

        return loan_history

    def __getAccount(self, account_num):
        try:
            # Prepare payload for Accounts API
            payload = {
                "account_number": account_num
            }
            logging.debug(f"Sending POST request to Accounts Service to get account details: {payload}")

            # Send POST request to Accounts Service's /account-detail endpoint
            response = requests.post(f"{ACCOUNTS_SERVICE_URL}/account-detail", json=payload, timeout=5)

            # Check HTTP status code
            if response.status_code != 200:
                logging.error(f"Error in request to Accounts Service: {response.status_code} - {response.text}")
                return None

            # Process response
            account = response.json()
            if account:
                logging.debug(f"Account details retrieved: {account}")
                return account
            else:
                logging.debug("No account found with the provided account number.")
                return None

        except requests.exceptions.RequestException as e:
            logging.error(f"Exception during communication with Accounts Service: {e}")
            return None
        except ValueError as e:
            logging.error(f"Error parsing JSON response: {e}")
            return None


    def __approveLoan(self, account, amount):
        if amount < 1:
            logging.debug("Loan amount less than minimum required.")
            return False

        new_balance = account["balance"] + amount

        # Prepare payload for updating balance
        payload = {
            "account_number": account["account_number"],
            "new_balance": new_balance
        }

        try:
            logging.debug(f"Sending POST request to Accounts Service to update balance: {payload}")

            # Send POST request to Accounts Service's /update-balance endpoint
            response = requests.post(f"{ACCOUNTS_SERVICE_URL}/update-balance", json=payload, timeout=5)

            # Check HTTP status code
            if response.status_code == 200:
                result = response.json()
                if result.get("success"):
                    logging.debug("Balance updated successfully via Accounts Service.")
                    return True
                else:
                    logging.error("Failed to update balance via Accounts Service.")
                    return False
            else:
                logging.error(f"Error updating balance via Accounts Service: {response.status_code} - {response.text}")
                return False

        except requests.exceptions.RequestException as e:
            logging.error(f"Exception during communication with Accounts Service: {e}")
            return False
        except ValueError as e:
            logging.error(f"Error parsing JSON response: {e}")
            return False


class LoanService(loan_pb2_grpc.LoanServiceServicer):
    def __init__(self) -> None:
        super().__init__()
        # enable github copiolot
        self.loan = LoanGeneric()

    def ProcessLoanRequest(self, request, context):
        name = request.name
        email = request.email
        account_type = request.account_type
        account_number = request.account_number
        govt_id_type = request.govt_id_type
        govt_id_number = request.govt_id_number
        loan_type = request.loan_type
        loan_amount = float(request.loan_amount)
        interest_rate = float(request.interest_rate)
        time_period = request.time_period

        req = {'name': name, 'email': email, 'account_type': account_type, 'account_number': account_number, 'govt_id_type': govt_id_type, 'govt_id_number': govt_id_number, 'loan_type': loan_type, 'loan_amount': loan_amount, 'interest_rate': interest_rate, 'time_period': time_period}
        resutl = self.loan.ProcessLoanRequest(req)  

        response =  LoanResponse(approved=resutl['approved'],  message=resutl['message'])
        return response

    def getLoanHistory(self, request, context):

        email = request.email
        req = {'email': email}
        loan_history = []

        loans = self.loan.getLoanHistory(req)

        for l in loans:
            loan_history.append(Loan(name=l['name'], email=l['email'], account_type=l['account_type'], account_number=l['account_number'], govt_id_type=l['govt_id_type'], govt_id_number=l['govt_id_number'], loan_type=l['loan_type'], loan_amount=l['loan_amount'], interest_rate=l['interest_rate'], time_period=l['time_period'], status=l['status'], timestamp=f"{l['timestamp']}"))
        
        return LoansHistoryResponse(loans=loan_history)




app = Flask(__name__)
loan_generic = LoanGeneric()
@app.route("/loan/request", methods=["POST"])
def process_loan_request():
    request_data = request.json
    logging.debug(f"Request: {request_data}")
    response = loan_generic.ProcessLoanRequest(request_data)
    return jsonify(response)


@app.route("/loan/history", methods=["POST"])
def get_loan_history():
    logging.debug("----------------> Request: /loan/history")
    d = request.json
    logging.debug(f"Request: {d}")
    response = loan_generic.getLoanHistory({"email": d['email']})
    return jsonify(response)




def serverGRPC(port):
    logging.debug(f"Starting GRPC server on port {port}")
    server = grpc.server(futures.ThreadPoolExecutor(max_workers=10))
    loan_pb2_grpc.add_LoanServiceServicer_to_server(LoanService(), server)
    server.add_insecure_port(f"[::]:{port}")
    server.start()
    server.wait_for_termination()

def serverFlask(port):
    logging.debug(f"Starting Flask server on port {port}")
    app.run(host='0.0.0.0' ,port=port, debug=True)


if __name__ == "__main__":
    port =  50053

    if protocol == "grpc":
        serverGRPC(port)
    else:
        serverFlask(port)




