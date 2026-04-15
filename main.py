from agent.conversation import ConversationEngine


def main():
    engine = ConversationEngine()

    result = engine.run(
        prospect_name="Sarah",
        persona="skeptical"
    )


if __name__ == "__main__":
    main()
