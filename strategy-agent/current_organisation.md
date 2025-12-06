Current organisation structure in strategy-agent: \\ \\

-flaskapp.py is main app \\ \\

-fetchdata.py is for fetching data from the price-engine. I will add DB fetch later \\
-confighelper.py is for the ABIs and helper functions regarding requests\\
\\
-datatypes.py is for data types and state \\
-gen_intent.py is for creating QuoteIntent which is what will be turned into a contract \\
and propogated to the chain \\
-enforcer.py enforces the policy, feasibility, and updates the state \\ \\

-requirements.txt is for the python dependencies. there might be some unused libraries \\
