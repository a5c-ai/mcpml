"""
Schemas for sentiment analysis output.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SentimentType(str, Enum):
    """Type of sentiment"""
    POSITIVE = "positive"
    NEUTRAL = "neutral"
    NEGATIVE = "negative"
    MIXED = "mixed"


class SentimentAspect(BaseModel):
    """A specific aspect of the sentiment analysis"""
    aspect: str = Field(..., description="The aspect being analyzed")
    sentiment: SentimentType = Field(..., description="The sentiment of this aspect")
    explanation: str = Field(..., description="Explanation of why this sentiment was assigned")


class SentimentAnalysisOutput(BaseModel):
    """Output schema for sentiment analysis"""
    overall_sentiment: SentimentType = Field(..., description="The overall sentiment of the text")
    confidence: float = Field(..., description="Confidence score between 0.0 and 1.0", ge=0.0, le=1.0)
    aspects: List[SentimentAspect] = Field(default_factory=list, description="Analysis of specific aspects of the text")
    summary: str = Field(..., description="A brief summary of the sentiment analysis")
    
    class Config:
        """Configuration for the model"""
        schema_extra = {
            "example": {
                "overall_sentiment": "positive",
                "confidence": 0.85,
                "aspects": [
                    {
                        "aspect": "customer service",
                        "sentiment": "positive",
                        "explanation": "The text mentions excellent customer support and responsiveness"
                    },
                    {
                        "aspect": "product quality",
                        "sentiment": "mixed",
                        "explanation": "While the product is praised for design, there are concerns about durability"
                    }
                ],
                "summary": "The text is generally positive, especially about customer service, with some minor concerns about product durability."
            }
        } 