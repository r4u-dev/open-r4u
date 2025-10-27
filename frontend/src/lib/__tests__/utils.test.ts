import { describe, it, expect } from "vitest";
import { extractFunctionName } from "../utils";

describe("extractFunctionName", () => {
    it("should extract function name from full path with arrow chain", () => {
        const path = "examples/templated_prompts_example.py::main->make_greeting_request";
        expect(extractFunctionName(path)).toBe("make_greeting_request");
    });

    it("should extract function name from simple path with double colon", () => {
        const path = "src/app.py::handler";
        expect(extractFunctionName(path)).toBe("handler");
    });

    it("should extract function name from path with multiple arrows", () => {
        const path = "src/services/api.py::process->validate->execute";
        expect(extractFunctionName(path)).toBe("execute");
    });

    it("should extract function name from path without file", () => {
        const path = "::main->helper";
        expect(extractFunctionName(path)).toBe("helper");
    });

    it("should handle path with only arrows (no double colon)", () => {
        const path = "main->helper->process";
        expect(extractFunctionName(path)).toBe("process");
    });

    it("should handle path with only function name", () => {
        const path = "my_function";
        expect(extractFunctionName(path)).toBe("my_function");
    });

    it("should return null for null input", () => {
        expect(extractFunctionName(null)).toBeNull();
    });

    it("should return null for empty string", () => {
        expect(extractFunctionName("")).toBeNull();
    });

    it("should handle whitespace in function name", () => {
        const path = "src/app.py::main->  helper_func  ";
        expect(extractFunctionName(path)).toBe("helper_func");
    });

    it("should handle complex real-world path", () => {
        const path = "backend/app/services/llm.py::LLMService.generate->_prepare_request->_validate_inputs";
        expect(extractFunctionName(path)).toBe("_validate_inputs");
    });

    it("should handle path with special characters", () => {
        const path = "src/test_file.py::TestClass::test_method->setUp";
        expect(extractFunctionName(path)).toBe("setUp");
    });
});
