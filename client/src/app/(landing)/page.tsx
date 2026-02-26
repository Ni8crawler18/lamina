import Hero from "@/components/landing/hero";
import HowItWorks from "@/components/landing/how-it-works";
import Features from "@/components/landing/features";
import Regulatory from "@/components/landing/regulatory";
import HederaIntegration from "@/components/landing/hedera-integration";
import Footer from "@/components/landing/footer";

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      <Hero />
      <HowItWorks />
      <Features />
      <Regulatory />
      <HederaIntegration />
      <Footer />
    </div>
  );
}
