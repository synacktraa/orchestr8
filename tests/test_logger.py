import pytest
from loguru import logger

from orchestr8.logger import Logger


@pytest.fixture
def caplog(caplog):
    handler_id = logger.add(caplog.handler, format="{message}")
    yield caplog
    logger.remove(handler_id)


class TestLoggerClass:
    def test_default_logger_initialization(self, caplog):
        """
        Verify that a subclass of Logger initializes with default logging configuration.
        """

        class DefaultLoggedClass(Logger):
            def test_method(self):
                self.logger.info("Test log message")

        # Create instance and call method
        instance = DefaultLoggedClass()
        instance.test_method()

        # Check captured log
        assert "Test log message" in caplog.text
        assert len(caplog.records) == 1

    def test_custom_logger_format(self, caplog):
        """
        Ensure custom logging format can be applied during class definition.
        """
        custom_format = "<level>{message}</level>"

        class CustomFormatClass(Logger, format=custom_format):
            def test_method(self):
                self.logger.info("Custom format test")

        # Create instance and call method
        instance = CustomFormatClass()
        instance.test_method()

        # Check captured log
        assert "Custom format test" in caplog.text
        assert len(caplog.records) == 1

    def test_class_method_logging(self, caplog):
        """
        Verify logging works correctly with class methods.
        """

        class ClassMethodLogger(Logger):
            @classmethod
            def log_method(cls):
                cls.logger.info("Class method logging")

        # Call class method
        ClassMethodLogger.log_method()

        # Check captured log
        assert "Class method logging" in caplog.text
        assert len(caplog.records) == 1

    def test_multiple_class_logging(self, caplog):
        """
        Ensure separate classes have independent logging contexts.
        """

        class FirstLogger(Logger):
            def log_first(self):
                self.logger.info("First logger message")

        class SecondLogger(Logger):
            def log_second(self):
                self.logger.info("Second logger message")

        # Log from both classes
        first_instance = FirstLogger()
        second_instance = SecondLogger()
        first_instance.log_first()
        second_instance.log_second()

        # Check captured logs
        assert "First logger message" in caplog.text
        assert "Second logger message" in caplog.text
        assert len(caplog.records) == 2

    def test_inheritance_logging(self, caplog):
        """
        Verify logging functionality works with class inheritance.
        """

        class BaseLogger(Logger):
            def base_log(self):
                self.logger.info("Base logger message")

        class InheritedLogger(BaseLogger):
            def inherited_log(self):
                self.logger.info("Inherited logger message")

        # Log from inherited class
        instance = InheritedLogger()
        instance.base_log()
        instance.inherited_log()

        # Check captured logs
        assert "Base logger message" in caplog.text
        assert "Inherited logger message" in caplog.text
        assert len(caplog.records) == 2

    def test_logger_binding_and_extras(self, caplog):
        """
        Ensure additional context can be bound to loggers.
        """

        class ContextLogger(Logger):
            def __init__(self, extra_context):
                self.context_logger = self.logger.bind(context=extra_context)

            def log_with_context(self):
                self.context_logger.info("Contextual logging")

        # Log with context
        instance = ContextLogger("test_context")
        instance.log_with_context()

        # Check captured log
        assert "Contextual logging" in caplog.text
        assert len(caplog.records) == 1
