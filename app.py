import os
import time
# Use the package we installed
from slack_bolt import App, BoltContext, Ack
from slack_bolt.response import BoltResponse
from flask import Flask, Response, request, jsonify, make_response
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_sdk.oauth import AuthorizeUrlGenerator
from auth import crypt
import utils
from auth import oauth
from typing import Optional, Dict, Callable, Sequence

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

flask_app = Flask(__name__)

# Initializes your app with your bot token and signing secret
oauth = oauth.CFOAuthSettings(os.environ.get("SLACK_CLIENT_ID"), os.environ.get("SLACK_CLIENT_SECRET"))
print(oauth.get_settings())
#token is not needed when using oauth
app = App(
  #token=os.environ.get("SLACK_BOT_TOKEN"),
  signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
  oauth_settings=oauth.get_settings(),
)
handler = SlackRequestHandler(app)

# @app.middleware
# def set_user_token_if_exists(context: BoltContext, next: Callable):
#     installation = user_installation_store.find_installation(
#         enterprise_id=context.enterprise_id,
#         team_id=context.team_id,
#         user_id=context.user_id,
#         is_enterprise_install=context.is_enterprise_install,
#     )
#     if installation is not None:
#         context["user_token"] = installation.user_token
#     next()


@app.event("app_home_opened")
def update_home_tab(client, event, logger):
  print(os.environ.get("SLACK_BOT_TOKEN"))
  print(os.environ.get("SLACK_SIGNING_SECRET"))
  try:
    # views.publish is the method that your app uses to push a view to the Home tab
    client.views_publish(
      # the user that opened your app's app home
      user_id=event["user"],
      # the view object that appears in the app home
      view={
        "type": "home",
        "callback_id": "home_view",

        # body of the view
        "blocks": [
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "*Welcome to your _App's Home_* :tada:"
            }
          },
          {
            "type": "divider"
          },
          {
            "type": "section",
            "text": {
              "type": "mrkdwn",
              "text": "This button won't do much for now but you can set up a listener for it using the `actions()` method and passing its unique `action_id`. See an example in the `examples` folder within your Bolt app."
            }
          },
          {
            "type": "actions",
            "elements": [
              {
                "type": "button",
                "text": {
                  "type": "plain_text",
                  "text": "Click me!"
                }
              }
            ]
          }
        ]
      }
    )
  
  except Exception as e:
    logger.error(f"Error publishing home tab: {e}")


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/slack/install", methods=["GET"])
def install():
    test_crpt = crypt.Crypt()
    test_key = 'MyKey4TestingYnP'
    merchant_id = request.args["merchant_id"]
    input_key = str(time.time_ns() // 1_000_000 ) + "|" + merchant_id
    # state = oauth.get_state_store().issue()
    state = oauth.issue_state(merchant_id)
    authorize_url_generator = AuthorizeUrlGenerator(
      client_id=os.environ["SLACK_CLIENT_ID"],
      scopes=oauth.get_scopes(),
    )
    url = authorize_url_generator.generate(state)
    set_cookie_value = oauth.get_settings().state_utils.build_set_cookie_for_new_state(state)
    bolt_response = BoltResponse(
      status=302,
      body="",
      headers=append_set_cookie_headers(
        {"Content-Type": "text/html; charset=utf-8", "Location": url},
        set_cookie_value,
      ),
    )
    return to_flask_response(bolt_response)
    # return handler.handle(request)



@flask_app.route("/slack/oauth_redirect", methods=["GET"])
def oauth_redirect():
    state = request.args.get("state", [None])[0]
    print("-->", oauth.get_settings().state_utils.is_valid_browser(state, request.headers))
    for k in request.args.keys():
      print(k, ":",  request.args[k])
    for k in request.headers.keys():
      print(k, ":",  request.headers[k])
    oauth.save_merchant_installation("", "17")
    return handler.handle(request)

@flask_app.route("/channels", methods=["GET"])
def get_channels():
  client = WebClient(token="xoxb-3719312487555-3732040431233-e9SmApQoSp1pGXQdUkH19srO")
  conversations_store = {}
  try:
    # Call the conversations.list method using the WebClient
    result = client.conversations_list()
    save_conversations(result["channels"], conversations_store)

  except SlackApiError as e:
    logger.error("Error fetching conversations: {}".format(e))

  print(conversations_store)
  return jsonify(
    data=conversations_store
  )


@flask_app.route("/slack/command", methods=["POST"])
def commands():
  print(request.headers)
  print(request.form)
  return jsonify(
    ok=200
  )



def save_conversations(conversations, conversations_store):
    conversation_id = ""
    for conversation in conversations:
      # Key conversation info on its unique ID
      conversation_id = conversation["id"]

      # Store the entire conversation object
      # (you may not need all of the info)
      conversations_store[conversation_id] = conversation

def to_flask_response(bolt_resp: BoltResponse) -> Response:
  resp: Response = make_response(bolt_resp.body, bolt_resp.status)
  for k, values in bolt_resp.headers.items():
    if k.lower() == "content-type" and resp.headers.get("content-type") is not None:
      # Remove the one set by Flask
      resp.headers.pop("content-type")
    for v in values:
      resp.headers.add_header(k, v)
  return resp


def append_set_cookie_headers(headers: dict, set_cookie_value: Optional[str]):
  if set_cookie_value is not None:
    headers["Set-Cookie"] = [set_cookie_value]
  return headers



#Start your app
if __name__ == "__main__":
  flask_app.run(port=3000, debug=True)

