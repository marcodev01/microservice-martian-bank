# Copyright (c) 2023 Cisco Systems, Inc. and its affiliates All rights reserved.
# Use of this source code is governed by a BSD-style
# license that can be found in the LICENSE file.

from locust import HttpUser, task, SequentialTaskSet, between
from api_urls import ApiUrls
import random
from faker import Faker

fake = Faker()

class AccountUser(HttpUser):
    host = ApiUrls["VITE_ACCOUNTS_URL"]
    
    @task
    class AccountUserTasks(SequentialTaskSet):
        wait_time = between(2, 3)
        
        def on_start(self):
             # Basic user information
            self.user_data = {
                "name": fake.unique.name(),
                "email_id": fake.unique.email(),
                "government_id_type": random.choice(
                    ["Driver's License", "Passport", "SSN"]
                ),
                "govt_id_number": fake.unique.ssn(),
                "address": fake.unique.address(),
            }
            
            # List of available account types
            account_types = ["Checking", "Savings", "Money Market", "Investment"]
            
            # Create three different accounts
            for _ in range(3):
                # Select a random, unused account type
                selected_type = random.choice(account_types)
                account_types.remove(selected_type)
                
                # Update the account type and create the account
                self.user_data["account_type"] = selected_type
                self.client.post(
                    "/create",
                    data=self.user_data,
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
        
        @task(3)
        def get_all_accounts(self):
            self.client.post(
                "/allaccounts",
                data={"email_id": self.user_data["email_id"]},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
        
        @task(2)
        def get_particular_account(self):
            self.client.get(
                "/detail",
                data={"email": self.user_data["email_id"]},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )