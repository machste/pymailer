# Welcome to Pymailer

Hello {{ NICKNAME }},

{% if GENDER == "male" %}

You should definitely take a look at our new men's collection.

{% elif GENDER == "female" %}

There is sure to be something for you in the new accessories section of your
online shop.

{% else %}

You should checkout are beautiful rainbow flags.

{% endif %}

Before you browse our online shop, please check the following information:

 * **Firstname**: {{ FIRSTNAME }}
 * **Name**: {{ NAME }}
 * **E-Mail**: {{ EMAIL }}

Regards,  
{{ SENDER }}
