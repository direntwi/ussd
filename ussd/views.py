from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import logging

logging.basicConfig(
    level=logging.DEBUG,
    filename="logfile.log",
    format="%(asctime)s - %(levelname)s - %(message)s",
    filemode="a",
)

FEELING_OPTIONS = {"1": "Fine", "2": "Frisky", "3": "Not well"}

REASON_OPTIONS = {"1": "Money", "2": "Relationships", "3": "Health"}

sessions = {}


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


@csrf_exempt
def ussd_handler(request):
    logging.debug("Received a new USSD request.")
    if request.method != "POST":
        return JsonResponse(
            {"error": "Invalid request method. POST required."}, status=405
        )

    try:
        # Parse the incoming JSON request body
        request_data = json.loads(request.body.decode("utf-8"))
        logging.debug(f"Parsed request data: {request_data}")
    except json.JSONDecodeError as e:
        logging.error(f"JSON decoding failed: {e}")
        return JsonResponse({"error": "Invalid JSON format."}, status=400)

    # Extract necessary USSD fields from the request
    user_id = request_data.get("USERID", "").strip()  # USSD identifier
    msisdn = request_data.get("MSISDN", "").strip()  # User's phone number
    user_data = request_data.get("USERDATA", "").strip()  # User's input
    request_msgtype = request_data.get(
        "MSGTYPE", True
    )  # True if first request, False otherwise
    session_id = request_data.get("SESSIONID", "").strip()  # Unique session ID

    logging.info(
        f"Session ID: {session_id}, MSISDN: {msisdn}, MSGTYPE: {request_msgtype}, USERDATA: {user_data}"
    )
    # Initialize response dictionary
    response_data = {
        "USERID": user_id,
        "MSISDN": msisdn,
        "MSG": "",  # To be set based on user input
        "MSGTYPE": True,  # Will be updated based on the flow
    }

    # Retrieve existing session data or initialize a new session
    if session_id not in sessions:
        sessions[session_id] = {}
        logging.debug(f"Initialized new session for Session ID: {session_id}")

    session = sessions[session_id]

    if request_msgtype:
        # New Session: Parse the user_data and process all inputs sequentially
        # Expected user_data format: "*920*1802*1*2#"
        # Remove the shortcode and extension (*920*1802*)
        # First, remove leading '*' and trailing '#'
        if user_data.startswith("*"):
            user_data_clean = user_data.lstrip("*").rstrip("#")
            parts = user_data_clean.split("*")
            logging.debug(f"Cleaned user_data: {user_data_clean}, Parts: {parts}")

            # Check if parts[0] == '920' and parts[1] == '1802'
            if len(parts) >= 2 and parts[0] == "920" and parts[1] == "1802":
                inputs = parts[2:]  # Remaining inputs
            else:
                # Invalid shortcode or extension
                logging.error(f"Invalid shortcode or extension: {parts[:2]}")
                response_data["MSG"] = (
                    "Invalid shortcode or extension. Please try again."
                )
                response_data["MSGTYPE"] = False  # Terminate session
                del sessions[session_id]
                return JsonResponse(response_data)
        else:
            # Invalid format for a new session
            logging.error(
                f"Invalid request format. user_data does not start with '*': {user_data}"
            )
            response_data["MSG"] = "Invalid request format. Please try again."
            response_data["MSGTYPE"] = False  # Terminate session
            del sessions[session_id]
            return JsonResponse(response_data)

        # Initialize state to 1 (Screen 1)
        session["state"] = 1
        logging.debug(
            f"Set session state to {session['state']} for Session ID: {session_id}"
        )

        # If no inputs are present after shortcode and extension, present Screen 1
        if not inputs:
            response_data["MSG"] = (
                f"Welcome to {user_id}'s Service.\n"
                "How are you feeling?\n"
                "1. Fine\n2. Frisky\n3. Not well"
            )
            logging.info(f"Presented Screen 1 to Session ID: {session_id}")
            # State remains 1
        else:
            # Process each input sequentially
            for input_value in inputs:
                logging.debug(
                    f"Processing input: {input_value} for Session ID: {session_id}"
                )
                current_state = session.get("state", 1)

                if current_state == 1:
                    # Processing Screen 1 Response: How are you feeling?
                    feeling = FEELING_OPTIONS.get(input_value)
                    if feeling:
                        # Valid input: Proceed to Screen 2
                        session["feeling"] = feeling
                        session["state"] = 2
                        response_data["MSG"] = (
                            f"Why are you feeling {feeling.lower()}?\n"
                            "1. Money\n2. Relationships\n3. Health"
                        )
                        logging.info(
                            f"Valid input on Screen 1: {input_value} ({feeling}) for Session ID: {session_id}"
                        )
                    else:
                        # Invalid Input on Screen 1: Reiterate Screen 1
                        response_data["MSG"] = (
                            "Invalid option selected. Please try again.\n"
                            "How are you feeling?\n"
                            "1. Fine\n2. Frisky\n3. Not well"
                        )
                        logging.warning(
                            f"Invalid input on Screen 1: {input_value} for Session ID: {session_id}"
                        )
                        break  # Stop processing further inputs

                elif current_state == 2:
                    # Processing Screen 2 Response: Why are you feeling {feeling}?
                    reason = REASON_OPTIONS.get(input_value)
                    if reason:
                        # Valid input: End session with summary
                        feeling = session.get("feeling", "N/A")
                        response_data["MSG"] = (
                            f"You are feeling {feeling.lower()} because of {reason.lower()}."
                        )
                        logging.info(
                            f"Valid input on Screen 2: {input_value} ({reason}) for Session ID: {session_id}"
                        )
                        response_data["MSGTYPE"] = False  # Terminate session
                        # Clean up session data
                        del sessions[session_id]
                    else:
                        # Invalid Input on Screen 2: Reiterate Screen 2
                        feeling = session.get("feeling", "N/A")
                        response_data["MSG"] = (
                            "Invalid option selected. Please try again.\n"
                            f"Why are you feeling {feeling.lower()}?\n"
                            "1. Money\n2. Relationships\n3. Health"
                        )
                        logging.warning(
                            f"Invalid input on Screen 2: {input_value} for Session ID: {session_id}"
                        )
                        # State remains 2
                    # Whether valid or invalid input, after processing, stop further inputs
                    break

                else:
                    # Undefined State: End session with error message
                    response_data["MSG"] = "An error occurred. Please try again later."
                    response_data["MSGTYPE"] = False  # Terminate session
                    logging.error(
                        f"Undefined state {current_state} for Session ID: {session_id}"
                    )
                    # Clean up session data
                    del sessions[session_id]
                    break  # Stop processing further inputs

    else:
        # Existing Session: Process the latest input
        # user_data contains the latest input, not concatenated
        input_value = user_data
        logging.debug(f"Latest input: {input_value} for Session ID: {session_id}")
        current_state = session.get("state", 1)

        if current_state == 1:
            # Processing Screen 1 Response: How are you feeling?
            feeling = FEELING_OPTIONS.get(input_value)
            if feeling:
                # Valid input: Proceed to Screen 2
                session["feeling"] = feeling
                session["state"] = 2
                response_data["MSG"] = (
                    f"Why are you feeling {feeling.lower()}?\n"
                    "1. Money\n2. Relationships\n3. Health"
                )
                logging.info(
                    f"Valid input on Screen 1: {input_value} ({feeling}) for Session ID: {session_id}"
                )
            else:
                # Invalid Input on Screen 1: Reiterate Screen 1
                response_data["MSG"] = (
                    "Invalid option selected. Please try again.\n"
                    "How are you feeling?\n"
                    "1. Fine\n2. Frisky\n3. Not well"
                )
                logging.warning(
                    f"Invalid input on Screen 1: {input_value} for Session ID: {session_id}"
                )
                # State remains 1

        elif current_state == 2:
            # Processing Screen 2 Response: Why are you feeling {feeling}?
            reason = REASON_OPTIONS.get(input_value)
            if reason:
                # Valid input: End session with summary
                feeling = session.get("feeling", "N/A")
                response_data["MSG"] = (
                    f"You are feeling {feeling.lower()} because of {reason.lower()}."
                )
                response_data["MSGTYPE"] = False  # Terminate session
                # Clean up session data
                del sessions[session_id]
                logging.info(
                    f"Valid input on Screen 2: {input_value} ({reason}) for Session ID: {session_id}"
                )
            else:
                # Invalid Input on Screen 2: Reiterate Screen 2
                feeling = session.get("feeling", "N/A")
                response_data["MSG"] = (
                    "Invalid option selected. Please try again.\n"
                    f"Why are you feeling {feeling.lower()}?\n"
                    "1. Money\n2. Relationships\n3. Health"
                )
                logging.warning(
                    f"Invalid input on Screen 2: {input_value} for Session ID: {session_id}"
                )
                # State remains 2

        else:
            # Undefined State: End session with error message
            response_data["MSG"] = "An error occurred. Please try again later."
            response_data["MSGTYPE"] = False  # Terminate session
            # Clean up session data
            del sessions[session_id]
            logging.error(
                f"Undefined state {current_state} for Session ID: {session_id}"
            )

    # Save the updated session data only if session exists
    if session_id in sessions:
        sessions[session_id] = session
    logging.debug(f"Response data: {response_data}")

    return JsonResponse(response_data)
