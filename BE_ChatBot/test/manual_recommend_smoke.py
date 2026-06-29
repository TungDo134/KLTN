import asyncio

from src.pipeline.inference import RAGInference


async def main():
    inference = RAGInference()
    await inference.predict_async(
        "Tôi muốn đi Đà Lạt 2 ngày, thích cafe và thác nước",
        session_id="test-recommend",
    )


if __name__ == "__main__":
    asyncio.run(main())
