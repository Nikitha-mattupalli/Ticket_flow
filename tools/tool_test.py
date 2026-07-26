# # from tools.billing_tools import fetch_invoice

# # result = fetch_invoice.invoke(
# #     {
# #         "customer_id": "7facde9a-4364-4766-a3b6-617e17785318"
# #     }
# # )

# # print(result)


# from tools.billing_tools import process_refund


# result = process_refund.invoke(
#     {
#         "payment_intent_id": "pi_3TxPtuJKgPUbZUXn1NRbLhb7",
#         "amount": 100000,
#         "reason": "duplicate",
#     }
# )

# print(result)

from tools.billing_tools import send_confirmation


result = send_confirmation.invoke(
    {
        "customer_email": "mattupallinikitha@gmail.com",
        "subject": "Refund confirmation",
        "message": (
            "Your refund request has been processed successfully. "
            "The amount will be returned to your original payment method."
        ),
    }
)

print(result)