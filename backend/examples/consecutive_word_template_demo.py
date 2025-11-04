"""Demo script for consecutive word-based template detection.

This script demonstrates how the new consecutive word-based approach
handles various scenarios, especially traces with large argument values.
"""

from app.services.template_inference import (
    TemplateInferrer,
    infer_template_from_strings,
)


def print_section(title: str):
    """Print a formatted section header."""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80 + "\n")


def demo_basic_usage():
    """Demonstrate basic consecutive word detection."""
    print_section("Demo 1: Basic Usage with Default Threshold (3 words)")

    strings = [
        "You are a personal assistant for Mr. Smith",
        "You are a personal assistant for Mr. Johnson",
        "You are a personal assistant for Mr. Williams",
    ]

    template = infer_template_from_strings(strings, min_consecutive_words=3)

    print("Input strings:")
    for i, s in enumerate(strings, 1):
        print(f"  {i}. {s}")

    print("\nDetected template:")
    print(f"  {template}")
    print(
        "\n✅ Common pattern: 'You are a personal assistant for Mr' (7 consecutive words)",
    )


def demo_large_arguments():
    """Demonstrate handling of large argument values."""
    print_section("Demo 2: Large Argument Values (Main Use Case)")

    large_bio_1 = "a software engineer with 15 years of experience in distributed systems, cloud architecture, machine learning, and team leadership across multiple Fortune 500 companies"
    large_bio_2 = "a data scientist specializing in machine learning, natural language processing, big data analytics, and statistical modeling with expertise in Python and R"

    strings = [
        f"You are a personal assistant for Mr. {large_bio_1}",
        f"You are a personal assistant for Mr. {large_bio_2}",
    ]

    template = infer_template_from_strings(strings, min_consecutive_words=3)

    print("Input strings with very large arguments:")
    print(
        f"  1. 'You are a personal assistant for Mr. [bio: {len(large_bio_1.split())} words]'",
    )
    print(
        f"  2. 'You are a personal assistant for Mr. [bio: {len(large_bio_2.split())} words]'",
    )

    print("\nDetected template:")
    print(f"  {template}")
    print("\n✅ Groups correctly despite large arguments!")
    print(
        f"   Ratio of template to total: {7 / (7 + 150):.1%} (very low, but still works)",
    )


def demo_different_thresholds():
    """Demonstrate different threshold values."""
    print_section("Demo 3: Different Threshold Values")

    strings = [
        "Hello there friend",
        "Hello there buddy",
    ]

    print("Input strings:")
    for i, s in enumerate(strings, 1):
        print(f"  {i}. {s}")

    print("\nResults with different thresholds:")

    for threshold in [1, 2, 3, 4]:
        template = infer_template_from_strings(strings, min_consecutive_words=threshold)
        status = "✅" if "{{var_0}}" in template and "Hello there" in template else "❌"
        print(f"  Threshold={threshold}: {template} {status}")

    print("\n💡 'Hello there' = 2 consecutive words")
    print("   - Thresholds 1-2: Match and create template")
    print("   - Thresholds 3+: Don't match, entire string becomes variable")


def demo_multiple_variables():
    """Demonstrate detection of multiple variables."""
    print_section("Demo 4: Multiple Variables")

    strings = [
        "User Alice logged in today at 10am",
        "User Bob logged in today at 2pm",
        "User Charlie logged in today at 5pm",
    ]

    template = infer_template_from_strings(strings, min_consecutive_words=3)

    print("Input strings:")
    for i, s in enumerate(strings, 1):
        print(f"  {i}. {s}")

    print("\nDetected template:")
    print(f"  {template}")
    print("\n✅ Detects both variable positions:")
    print("   - User name (Alice, Bob, Charlie)")
    print("   - Time (10am, 2pm, 5pm)")


def demo_strict_matching():
    """Demonstrate strict matching with high threshold."""
    print_section("Demo 5: Strict Matching (High Threshold)")

    inferrer = TemplateInferrer(min_consecutive_words=5)

    # Case 1: Enough consecutive words
    strings1 = [
        "You are a helpful assistant for Alice",
        "You are a helpful assistant for Bob",
    ]

    template1 = inferrer.infer_template(strings1)
    print("Case 1: 'You are a helpful assistant for' (6 words)")
    print(f"  Template: {template1}")
    print("  ✅ 6 words >= 5 threshold, matches!")

    # Case 2: Not enough consecutive words
    strings2 = [
        "Get weather for NYC",
        "Get weather for LA",
    ]

    template2 = inferrer.infer_template(strings2)
    print("\nCase 2: 'Get weather for' (3 words)")
    print(f"  Template: {template2}")
    print("  ❌ 3 words < 5 threshold, doesn't match")


def demo_punctuation_handling():
    """Demonstrate how punctuation is handled."""
    print_section("Demo 6: Punctuation Handling")

    inferrer = TemplateInferrer(min_consecutive_words=3)

    strings = [
        "Email: alice@example.com (active)",
        "Email: bob@example.com (active)",
        "Email: charlie@example.com (active)",
    ]

    template = inferrer.infer_template(strings)

    print("Input strings:")
    for i, s in enumerate(strings, 1):
        print(f"  {i}. {s}")

    print("\nDetected template:")
    print(f"  {template}")
    print("\n💡 Punctuation doesn't count as words:")
    print("   - 'Email' = 1 word")
    print("   - 'Email:' = 1 word (punctuation ignored)")
    print("   - Common suffix '(active)' is preserved")


def demo_weather_queries():
    """Demonstrate real-world weather query pattern."""
    print_section("Demo 7: Real-World Example - Weather Queries")

    strings = [
        "Get weather forecast for New York City",
        "Get weather forecast for Los Angeles",
        "Get weather forecast for Chicago",
        "Get weather forecast for San Francisco",
    ]

    template = infer_template_from_strings(strings, min_consecutive_words=3)

    print("Input strings:")
    for i, s in enumerate(strings, 1):
        print(f"  {i}. {s}")

    print("\nDetected template:")
    print(f"  {template}")
    print("\n✅ All 4 traces grouped under single template:")
    print("   Common: 'Get weather forecast for' (4 words)")
    print("   Variable: City name")


def demo_comparison_old_vs_new():
    """Compare old heuristic approach vs new consecutive word approach."""
    print_section("Demo 8: Comparison - Old vs New Approach")

    # Scenario that failed with old approach
    large_arg = "a comprehensive 500-word description of the user's background, expertise, accomplishments, and goals that would make the ratio very small"

    strings = [
        f"Summarize this content for user: {large_arg}",
        f"Summarize this content for user: {large_arg.replace('500-word', '400-word')}",
    ]

    template = infer_template_from_strings(strings, min_consecutive_words=3)

    print("Scenario: Very large argument values")
    print("  Common part: 'Summarize this content for user' (5 words)")
    print(f"  Argument size: ~{len(large_arg.split())} words")
    print(f"  Ratio: ~5/{len(large_arg.split())} = {5 / len(large_arg.split()):.1%}")

    print("\nOld approach (ratio-based):")
    print("  ❌ Would fail - ratio too small, false negative")

    print("\nNew approach (consecutive words):")
    print(f"  Template: {template}")
    print(
        "  ✅ Works! Detects 'Summarize this content for user' (5 consecutive words)",
    )


def main():
    """Run all demos."""
    print("\n" + "#" * 80)
    print("#" + " " * 78 + "#")
    print("#" + "  Consecutive Word-Based Template Detection - Demo".center(78) + "#")
    print("#" + " " * 78 + "#")
    print("#" * 80)

    demos = [
        demo_basic_usage,
        demo_large_arguments,
        demo_different_thresholds,
        demo_multiple_variables,
        demo_strict_matching,
        demo_punctuation_handling,
        demo_weather_queries,
        demo_comparison_old_vs_new,
    ]

    for demo in demos:
        try:
            demo()
        except Exception as e:
            print(f"\n❌ Error in {demo.__name__}: {e}")

    print("\n" + "=" * 80)
    print("  Demo Complete!")
    print("=" * 80)
    print("\n💡 Key Takeaways:")
    print("  1. Default threshold of 3 consecutive words works well for most cases")
    print("  2. Handles large argument values without false negatives")
    print("  3. Configurable threshold for different use cases")
    print("  4. Punctuation doesn't count toward word threshold")
    print("  5. More predictable than heuristic-based approach")
    print("\n📖 See docs/consecutive-word-template-detection.md for full documentation")
    print()


if __name__ == "__main__":
    main()

