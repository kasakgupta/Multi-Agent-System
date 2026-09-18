from agents import build_reader_agent, build_search_agent, writer_chain, critic_chain

def run_research_pipeline(topic: str) -> dict:
    state = {}

    #search agent working
    print("\n" + "="*50)
    print("step 1: Search Agent is gathering information...")
    print("="*50 + "\n")

    search_agent = build_search_agent()
    search_result =search_agent.invoke({
        "messages": [("user", f"Find recent and reliable information on the topic: {topic}")]
    })
    state["search_results"] = search_result['messages'][-1].content

    print("\n search result", state["search_results"])

    #step 2 : Reader Agent working
    print("\n" + "="*50)
    print("step 2: Reader Agent is scraping the URLs...")
    print("="*50 + "\n")

    reader_agent = build_reader_agent()
    reader_result =reader_agent.invoke({
        "messages": [("user",
                       f"Based on the search results about '{topic}',"
                       f"pick the most relevant URLs and scrape it for deeper content.\n\n"
                       f"Search Results:\n{state['search_results'][:800]}"
                       )]
                    })

    state['scraped_content'] = reader_result['messages'][-1].content

    print("\n scraped content", state['scraped_content'])

    #step 3 : Writer Chain working
    print("\n" + "="*50)
    print("step 3: Writer Chain is generating the research report...")
    print("="*50 + "\n")

    research_combined = (
        f"Search Results:\n{state['search_results']}\n\n"
        f"Scraped Content:\n{state['scraped_content']}"
    )

    state["report"] = writer_chain.invoke({
        "topic": topic,
        "research": research_combined
    })

    print("\n Final report", state["report"])

    #step 4 : Critic Chain working
    print("\n" + "="*50)
    print("step 4: Critic Chain is evaluating the research report...")
    print("="*50 + "\n")

    state["feedback"] = critic_chain.invoke({
        "report": state["report"]
    })

    print("\n critic feedback", state["feedback"])

    return state

if __name__ == "__main__":
    topic = input("\n Enter a research topic: ")
    run_research_pipeline(topic)