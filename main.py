from fastapi import FastAPI
from fastapi import Request
from fastapi.responses import JSONResponse
import new_helper
import generic_helper
app = FastAPI()

inprogress_orders = {}

@app.post("/")
async def handle_request(request: Request):
    # Retrieve the JSON data from the request
    payload = await request.json()

    # Extract the necessary information from the payload
    # based on the structure of the WebhookRequest from Dialogflow
    intent = payload['queryResult']['intent']['displayName']
    parameters = payload['queryResult']['parameters']
    output_contexts = payload['queryResult']['outputContexts']

    session_id=generic_helper.extract_session_id(output_contexts[0]['name'])

    intent_handler_dict={
            'order.add - context:ongoing-order':add_to_order,
            'order.remove - context:ongoing-order': remove_from_order,
            'order.complete - context:ongoing-order':complete_order,
            'track.order - context:ongoing-tracking':track_order
    }

    return intent_handler_dict[intent](parameters,session_id)

def remove_from_order(parameters: dict, session_id: str):
    if session_id not in inprogress_orders:
        return JSONResponse(content={
            "fulfillmentText": " I am having trouble finding your order. Sorry"
        })
    
    current_order=inprogress_orders[session_id]
    snacks= parameters["snacks"]

    removed_items=[]
    no_such_items=[]

    for item in snacks:
        if item not in current_order:
            no_such_items.append(item)

        else:
            del current_order[item]

    if len(removed_items)>0:
        fulfillment_text= f' Removed {",".join(removed_items)} from your order.'

    if len(no_such_items)>0:
        fulfillment_text=f'your current order does not have {",".join(no_such_items)}'

    if len(current_order.keys())==0:
        fulfillment_text += "Your order is empty"

    else:
        order_str=generic_helper.get_str_from_food_dict(current_order)
        fulfillment_text += f'Here is what is left in your order:{order_str}'

    return JSONResponse(content={
        "fulfillment_text" : fulfillment_text
    })

def extract_session_id(session_str:str):
    import re 
    match=re.search(r"/sessions/(.*?)/contexts/",session_str)
    if match:
        extarcted_string=match.group(0)
        return extarcted_string
    
    return ""

def add_to_order(parameters:dict, session_id:str):
    food_items= parameters["food-item"]
    quantities=parameters["number"]

    if len(food_items)!=len(quantities):
        fulfillment_text="Sorry i didn't understand. please specify the quantity"
    else:
        new_food_dict= dict(zip(food_items,quantities))

        if session_id in inprogress_orders:
            current_food_dict=inprogress_orders[session_id]
            current_food_dict.update(new_food_dict)
            inprogress_orders[session_id]=current_food_dict
        else:
            inprogress_orders[session_id]=new_food_dict


        order_str = generic_helper.get_str_from_food_dict(inprogress_orders[session_id])
        fulfillment_text=f"So far you have {order_str}. Do you need anything else?"


    return JSONResponse(content={
            "fulfillmentText": fulfillment_text
        })

def complete_order(parameters: dict, session_id:str):
    if session_id not in inprogress_orders:
        fulfillment_text="I am having trouble finding your order. can you place a new order."

    else:
        order=inprogress_orders[session_id]
        order_id=save_to_db(order)

        if order_id ==-1:
            fulfillment_text="Sorry I couldn't process your order due to some backend error."
        else:
            order_total= new_helper.get_total_order_price(order_id)
            fulfillment_text=f" Awesome .Your order is placed. "\
                             f" Here is your order id #{order_id}"
            
        del inprogress_orders[session_id]
    
    return JSONResponse(content={
        "fulfillmentText": fulfillment_text
    })            
            
            
            
def save_to_db(order:dict):
    next_order_id=new_helper.get_next_order_id()
    
    for snacks,quantity in order.items():
        new_helper.insert_order_item(
            snacks,
            quantity,
            next_order_id
        )

    new_helper.insert_order_tracking(next_order_id,"in progress")

    return next_order_id


def track_order(parameters :dict,session_id:str):
    order_id=int (parameters['order_id'])
    order_status=new_helper.get_order_status(order_id)

    if order_status:
        fulfillment_text=f"The order status for the order id is{order_id} is: {order_status}"
    else:
        fulfillment_text=f"No order found with order id: {order_id}"


    return JSONResponse(content={
            "fulfillmentText": fulfillment_text
        })
