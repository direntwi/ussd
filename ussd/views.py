from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json


@csrf_exempt
def debug_request_view(request):
    # Extracting request details
    request_details = {
        "method": request.method,
        "headers": dict(request.headers),
        "GET_params": request.GET.dict(),
        "POST_params": request.POST.dict(),
        "body": request.body.decode("utf-8"),
    }

    return JsonResponse(request_details)


# Optional: Define mapping dictionaries for cleaner code
FEELING_OPTIONS = {"1": "Fine", "2": "Frisky", "3": "Not well"}

REASON_OPTIONS = {"1": "Money", "2": "Relationships", "3": "Health"}

sessions = {}


@csrf_exempt
def ussd_handler(request):  # works so I'm using this
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. POST required."}, status=405
        )

    try:
        # Parse the incoming JSON request body
        request_data = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"Invalid JSON"}, status=400)

    # Extract necessary USSD fields from the request
    user_id = request_data.get("USERID", "").strip()  # USSD identifier, e.g., NOC1802
    msisdn = request_data.get("MSISDN", "").strip()  # User's phone number
    user_data = request_data.get("USERDATA", "").strip()  # User's input
    msgtype = request_data.get(
        "MSGTYPE", True
    )  # True if first request, False otherwise
    session_id = request_data.get("SESSIONID", "").strip()  # Unique session ID

    # Validate mandatory fields
    if not all([user_id, msisdn, session_id]):
        return JsonResponse({"error": "Missing required parameters."}, status=400)

    # Validate MSISDN format (simple check: digits only and length)
    if not msisdn.isdigit() or len(msisdn) < 10:
        return JsonResponse({"error": "Invalid MSISDN format."}, status=400)

    # Initialize response dictionary
    response_data = {
        "USERID": user_id,
        "MSISDN": msisdn,
        "MSGTYPE": True,  # Will be updated based on the flow
        "MSG": "",  # To be set based on user input
    }

    # Retrieve existing session data or initialize a new session
    if session_id not in sessions:
        sessions[session_id] = {}

    session = sessions[session_id]

    if msgtype:
        # **New Session**: Present Screen 1
        response_data["MSG"] = (
            f"Welcome to {user_id}'s Service.\n"
            "How are you feeling?\n"
            "1. Fine\n"
            "2. Frisky\n"
            "3. Not well"
        )
        response_data["MSGTYPE"] = True  # Session continues
        # Update session state
        session["state"] = 1
    else:
        # **Existing Session**: Determine current state and respond accordingly
        current_state = session.get("state", 1)  # Default to Screen 1 if not set

        if current_state == 1:
            # **Processing Screen 1 Response**: How are you feeling?
            feeling = FEELING_OPTIONS.get(user_data)
            if feeling:
                # Valid input: Proceed to Screen 2
                session["feeling"] = feeling
                session["state"] = 2
                response_data["MSG"] = (
                    f"Why are you feeling {feeling.lower()}?\n"
                    "1. Money\n"
                    "2. Relationships\n"
                    "3. Health"
                )
                response_data["MSGTYPE"] = True  # Session continues
            else:
                # **Invalid Input on Screen 1**: Reiterate Screen 1
                response_data["MSG"] = (
                    "Invalid option selected. Please try again.\n"
                    "How are you feeling?\n"
                    "1. Fine\n"
                    "2. Frisky\n"
                    "3. Not well"
                )
                response_data["MSGTYPE"] = True  # Session continues
                # State remains 1

        elif current_state == 2:
            # **Processing Screen 2 Response**: Why are you feeling {feeling}?
            reason = REASON_OPTIONS.get(user_data)
            if reason:
                # Valid input: End session with summary
                feeling = session.get("feeling", "N/A")
                response_data["MSG"] = (
                    f"You are feeling {feeling.lower()} because of {reason.lower()}."
                )
                response_data["MSGTYPE"] = False  # End session
                # Clean up session data
                del sessions[session_id]
            else:
                # **Invalid Input on Screen 2**: Reiterate Screen 2
                feeling = session.get("feeling", "N/A")
                response_data["MSG"] = (
                    "Invalid option selected. Please try again.\n"
                    f"Why are you feeling {feeling.lower()}?\n"
                    "1. Money\n"
                    "2. Relationships\n"
                    "3. Health"
                )
                response_data["MSGTYPE"] = True  # Session continues
                # State remains 2

        else:
            # **Undefined State**: End session with error message
            response_data["MSG"] = "An error occurred. Please try again later."
            response_data["MSGTYPE"] = False  # End session
            # Clean up session data
            del sessions[session_id]

    # Save the updated session data
    sessions[session_id] = session

    return JsonResponse(response_data)
