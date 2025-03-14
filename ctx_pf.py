import json
import os
from confluent_kafka import Consumer, KafkaError, KafkaException
import uuid
from google.protobuf.message import DecodeError
from solana.parsed_idl_block_message_pb2 import ParsedIdlBlockMessage
import base58

group_id_suffix = uuid.uuid4().hex

# Kafka consumer configuration
conf = {
    'bootstrap.servers': 'rpk0.bitquery.io:9093,rpk1.bitquery.io:9093,rpk2.bitquery.io:9093',
    'group.id': f'solana_105-group-{group_id_suffix}',  
    'session.timeout.ms': 30000,
    'security.protocol': 'SASL_SSL',
    'ssl.ca.location': '/Users/divyasshree/Documents/GitHub/kafka-example/server.cer.pem',
    'ssl.key.location': '/Users/divyasshree/Documents/GitHub/kafka-example/client.key.pem',
    'ssl.certificate.location': '/Users/divyasshree/Documents/GitHub/kafka-example/client.cer.pem',
    'ssl.endpoint.identification.algorithm': 'none',
    'sasl.mechanisms': 'SCRAM-SHA-512',
    'sasl.username': 'usernamee',
    'sasl.password': 'pwww',
    'auto.offset.reset': 'latest',
}

# Initialize Kafka consumer
consumer = Consumer(conf)
topic = 'solana.transactions.proto'

# Target account address to filter transactions
TARGET_ACCOUNT_ADDRESS = "TSLvdd1pWpHVjahSpsvCXUbgwsL3JAcvokwaKt1eokM"

def process_message(message):
    try:
        buffer = message.value()
        tx_block = ParsedIdlBlockMessage()
        tx_block.ParseFromString(buffer)

        print("\nNew Block Message Received")

        # Block Header
        if tx_block.HasField("Header"):
            header = tx_block.Header
            print(f"Block Slot: {header.Slot}")
           

        for tx in tx_block.Transactions:
            include_transaction = False

            # Check if the target account is involved in the transaction
            if tx.HasField("Header"):
                for account in tx.Header.Accounts:
                    account_address = base58.b58encode(account.Address).decode()
                    if account_address == TARGET_ACCOUNT_ADDRESS:
                        include_transaction = True
                        break  # Stop checking further, we found the account

            # If not found in the header accounts, check in instruction accounts
            if not include_transaction:
                for instruction in tx.ParsedIdlInstructions:
                    for account in instruction.Accounts:
                        account_address = base58.b58encode(account.Address).decode()
                        if account_address == TARGET_ACCOUNT_ADDRESS:
                            include_transaction = True
                            break  # Stop checking further, we found the account
                    if include_transaction:
                        break  # No need to check more instructions

            if not include_transaction:
                continue  # Skip this transaction as it doesn't contain the target account

            print("\nTransaction Details:")
            print(f"Transaction Signature: {base58.b58encode(tx.Signature).decode()}")
            print(f"Transaction Index: {tx.Index}")

            if tx.HasField("Status"):
                print(f"Transaction Status: {tx.Status.Success}")

            if tx.HasField("Header"):
                header = tx.Header
                print(f"Fee Payer: {base58.b58encode(header.FeePayer).decode()}")
                print(f"Fee: {header.Fee}")
                print(f"Recent Blockhash: {base58.b58encode(header.RecentBlockhash).decode()}")

                print("Signatures:")
                for sig in header.Signatures:
                    print(f"   {base58.b58encode(sig).decode()}")

                print("Accounts Involved:")
                for account in header.Accounts:
                    account_address = base58.b58encode(account.Address).decode()
                    print(f"   Address: {account_address}")
                    print(f"   Is Signer: {account.IsSigner}")
                    print(f"   Is Writable: {account.IsWritable}")

                    if account.HasField("Token"):
                        token = account.Token
                        print(f"      Token Mint: {base58.b58encode(token.Mint).decode()}")
                        print(f"      Owner: {base58.b58encode(token.Owner).decode()}")
                        print(f"      Decimals: {token.Decimals}")
                        print(f"      Program ID: {base58.b58encode(token.ProgramId).decode()}")

            for balance_update in tx.TotalBalanceUpdates:
                print(f"Balance Update: {balance_update.PreBalance} → {balance_update.PostBalance}")

            for token_balance_update in tx.TotalTokenBalanceUpdates:
                print(f"Token Balance Update: {token_balance_update.PreBalance} → {token_balance_update.PostBalance}")

            for instruction in tx.ParsedIdlInstructions:
                print("\nInstruction Details:")
                print(f"Instruction Index: {instruction.Index}")
                print(f"Caller Index: {instruction.CallerIndex}")
                print(f"Depth: {instruction.Depth}")

                if instruction.AncestorIndexes:
                    print(f"Ancestor Indexes: {list(instruction.AncestorIndexes)}")

                if instruction.HasField("Program"):
                    program = instruction.Program
                    print(f"Program Address: {base58.b58encode(program.Address).decode()}")
                    print(f"Program Name: {program.Name}")
                    print(f"Method Called: {program.Method}")

                for arg in program.Arguments:
                    print(f"Argument Name: {arg.Name}")
                    print(f"  Type: {arg.Type}")

                    if arg.HasField("String"):
                        print(f"  Value (String): {arg.String}")
                    elif arg.HasField("UInt"):
                        print(f"  Value (UInt): {arg.UInt}")
                    elif arg.HasField("Int"):
                        print(f"  Value (Int): {arg.Int}")
                    elif arg.HasField("Bool"):
                        print(f"  Value (Bool): {arg.Bool}")
                    elif arg.HasField("Float"):
                        print(f"  Value (Float): {arg.Float}")
                    elif arg.HasField("Json"):
                        print(f"  Value (Json): {arg.Json}")
                    elif arg.HasField("Address"):
                        print(f"  Value (Address): {base58.b58encode(arg.Address).decode()}")

                for account in instruction.Accounts:
                    account_address = base58.b58encode(account.Address).decode()
                    print(f"Instruction Account: {account_address}")

                for log in instruction.Logs:
                    print(f"Execution Log: {log}")

                for balance_update in instruction.BalanceUpdates:
                    print(f"Instruction Balance Update: {balance_update.PreBalance} → {balance_update.PostBalance}")

                for token_balance_update in instruction.TokenBalanceUpdates:
                    print(f"Instruction Token Balance Update: {token_balance_update.PreBalance} → {token_balance_update.PostBalance}")

    except DecodeError as err:
        print(f"Protobuf decoding error: {err}")
    except Exception as err:
        print(f"Error processing message: {err}")

# Subscribe to the topic
consumer.subscribe([topic])

# Poll messages and process them
try:
    while True:
        msg = consumer.poll(timeout=1.0)
        if msg is None:
            continue
        if msg.error():
            if msg.error().code() == KafkaError._PARTITION_EOF:
                continue
            else:
                raise KafkaException(msg.error())
        process_message(msg)

except KeyboardInterrupt:
    pass

finally:
    consumer.close()
