import Navigation from "@/components/layout/Navigation";
import Hero from "@/components/landing/Hero";
import ChatMockup from "@/components/landing/ChatMockup";
import HowItWorks from "@/components/landing/HowItWorks";
import Features from "@/components/landing/Features";
import Stats from "@/components/landing/Stats";
import Pricing from "@/components/landing/Pricing";
import FinalCTA from "@/components/landing/FinalCTA";
import Footer from "@/components/layout/Footer";
import LoginOverlay from "@/components/common/LoginOverlay";

export default function LandingPage() {
  return (
    <main className="min-h-screen bg-[#0A0F1C]">
      <Navigation />
      <Hero />
      <ChatMockup />
      <HowItWorks />
      <Features />
      <Stats />
      <Pricing />
      <FinalCTA />
      <Footer />
      <LoginOverlay />
    </main>
  );
}
