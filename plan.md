Now this is what I want to be implemented : 

This is going to be a Agentic-AI that is going to assist a Product Manager. This is going to be a POC, so lets make sure it works in a simulated environment rather than in production.

This is what the overall work flow should be : Instead of entering requirements through a prompt, all input documents should be placed into a structured input folder (e.g., `inputs/`) before the agent runs. Each department (customer support, sales, finance, tech, etc.) has its own subfolder or dedicated file inside `inputs/`. The agent reads these files directly at startup to build its context — no manual pasting into a prompt.

Example folder layout:
```
inputs/
  product_context.md
  customer_support.md
  sales.md
  finance.md
  tech.md
  employees.md
```

I want the ai agent to have a memory of all the departments, the employees and all other information that a product manager requires — all sourced by reading the files in the `inputs/` folder. 

I then want the ai agent to come up with whatever the product manager actually does, like making these : 
EPIC board
Product roadmaps
key focus areas
define clear requirement -> scope -> and the final
Pre and post success of the feature
Quadrant of effects and impact - 4 quadrants - always high impact (both low and high effect) is preferred.

Then I want the AI agent to create those and send mails to the respective people about the actions to be taken (by actually mailing them - will be giving google gmail api access keys). 

Then I want an interactive window/prompt to simulate real-life communication — accessible by anyone (customer support, sales, finance, tech, or the PM). Users identify their department/role before messaging. They can type in changes like new sales data, new employees joining and some leaving, infeasible tasks flagged by the PM, or any other instructions. This is the only place where direct prompt input is used; all initial context still comes from the `inputs/` folder.
We might need this to be something like a RAG system for easy getting data from the system and being able to update values.

Also there has to be something like

As this is a POC, I want this to be extensible in every layer. 
Can you review the above statements and provide a clear tasks to be done to the AI coding agent to build this Agentic-AI?