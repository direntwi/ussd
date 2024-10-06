from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse


import json


@csrf_exempt
def index(request):
    if request.method == "POST":
        try:
            # Parse the JSON data from the request body
            data = json.loads(request.body)
            print("POST Data (JSON):", data)

            # Extract parameters from the JSON data
            session_id = data.get("sessionId")
            service_code = data.get("serviceCode")
            phone_number = data.get("phoneNumber")
            text = data.get("text")

            print(
                f"Session ID: {session_id}, Service Code: {service_code}, Phone Number: {phone_number}, Text: {text}"
            )

            response = ""

            if text == "":
                response = f"CON {service_code}: What would you want to check \n"
                response += "1. My Phone Number"

            elif text == "1":
                response = f"END My Phone number is {phone_number}"

            print("Response:", response)

            return HttpResponse(response, content_type="text/plain")

        except json.JSONDecodeError:
            print("Invalid JSON received.")
            return HttpResponse("Invalid JSON", status=400)

    # If not a POST request, return a 405 Method Not Allowed response
    return HttpResponse("Invalid request method", status=405)
