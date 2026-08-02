import React, { useState, useEffect } from "react";
import { BusinessProfile, BusinessProfileCreate } from "../types";
import { apiService } from "../services/api";

interface BusinessConfigModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSaveSuccess: (profile: BusinessProfile) => void;
  currentProfile?: BusinessProfile | null;
}

export const BusinessConfigModal: React.FC<BusinessConfigModalProps> = ({
  isOpen,
  onClose,
  onSaveSuccess,
  currentProfile,
}) => {
  const [companyName, setCompanyName] = useState<string>("");
  const [productDescription, setProductDescription] = useState<string>("");
  const [pricingDetails, setPricingDetails] = useState<string>("");
  const [callObjective, setCallObjective] = useState<string>("");
  const [faqs, setFaqs] = useState<string[]>([""]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (currentProfile) {
      setCompanyName(currentProfile.company_name || "");
      setProductDescription(currentProfile.product_description || "");
      setPricingDetails(currentProfile.pricing_details || "");
      setCallObjective(currentProfile.call_objective || "");
      setFaqs(
        currentProfile.faqs && currentProfile.faqs.length > 0
          ? currentProfile.faqs
          : [""],
      );
    } else {
      setCompanyName("Surya Solar Solutions");
      setProductDescription(
        "We install residential and commercial rooftop solar power systems.",
      );
      setPricingDetails(
        "3kW system is ₹1,50,000. 40% government subsidy available.",
      );
      setCallObjective(
        "Qualify customer budget and schedule a free on-site consultation visit.",
      );
      setFaqs([
        "Installation takes 2 days.",
        "10-year comprehensive warranty included.",
      ]);
    }
  }, [currentProfile, isOpen]);

  if (!isOpen) return null;

  const handleAddFaq = () => {
    setFaqs((prev) => [...prev, ""]);
  };

  const handleFaqChange = (index: number, value: string) => {
    const updated = [...faqs];
    updated[index] = value;
    setFaqs(updated);
  };

  const handleRemoveFaq = (index: number) => {
    setFaqs((prev) => prev.filter((_, i) => i !== index));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsLoading(true);

    const cleanedFaqs = faqs.map((f) => f.trim()).filter((f) => f.length > 0);

    const payload: BusinessProfileCreate = {
      company_name: companyName.trim(),
      product_description: productDescription.trim(),
      pricing_details: pricingDetails.trim(),
      call_objective: callObjective.trim(),
      faqs: cleanedFaqs,
    };

    try {
      const savedProfile = await apiService.saveBusinessProfile(payload);
      onSaveSuccess(savedProfile);
      onClose();
    } catch (err: any) {
      console.error("Failed to save Business KB:", err);
      setError(
        err?.response?.data?.detail ||
          "Failed to update Business Knowledge Base.",
      );
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4">
      <div className="w-full max-w-2xl rounded-2xl bg-slate-900 border border-slate-800 shadow-2xl p-6 overflow-y-auto max-h-[90vh]">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4 mb-4">
          <div>
            <h2 className="text-xl font-bold text-white">
              AI Training & Knowledge Base
            </h2>
            <p className="text-sm text-slate-400">
              Configure products, pricing, and FAQs injected into Llama-3.3-70B
              during calls.
            </p>
          </div>
          <button
            onClick={onClose}
            className="text-slate-400 hover:text-white transition-colors"
            aria-label="Close modal"
          >
            ✕
          </button>
        </div>

        {error && (
          <div className="mb-4 rounded-lg bg-red-950/50 border border-red-800 p-3 text-sm text-red-300">
            {error}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Company Name
            </label>
            <input
              type="text"
              required
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              placeholder="e.g., Surya Solar Solutions"
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              What You Sell (Product / Service Description)
            </label>
            <textarea
              required
              rows={2}
              value={productDescription}
              onChange={(e) => setProductDescription(e.target.value)}
              placeholder="Describe your core offering..."
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Pricing, Subsidies & Current Offers
            </label>
            <textarea
              required
              rows={2}
              value={pricingDetails}
              onChange={(e) => setPricingDetails(e.target.value)}
              placeholder="e.g., 3kW system is ₹1,50,000. 40% subsidy available."
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <label className="block text-sm font-medium text-slate-300 mb-1">
              Primary Call Objective (CTA)
            </label>
            <input
              type="text"
              required
              value={callObjective}
              onChange={(e) => setCallObjective(e.target.value)}
              placeholder="e.g., Schedule a free on-site consultation visit"
              className="w-full rounded-lg bg-slate-800 border border-slate-700 px-3 py-2 text-white focus:border-indigo-500 focus:outline-none"
            />
          </div>

          <div>
            <div className="flex items-center justify-between mb-2">
              <label className="text-sm font-medium text-slate-300">
                Frequently Asked Questions (FAQs)
              </label>
              <button
                type="button"
                onClick={handleAddFaq}
                className="text-xs font-semibold text-indigo-400 hover:text-indigo-300"
              >
                + Add FAQ
              </button>
            </div>
            <div className="space-y-2">
              {faqs.map((faq, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <input
                    type="text"
                    value={faq}
                    onChange={(e) => handleFaqChange(idx, e.target.value)}
                    placeholder={`FAQ #${idx + 1} (e.g., Installation takes 2 days)`}
                    className="flex-1 rounded-lg bg-slate-800 border border-slate-700 px-3 py-1.5 text-sm text-white focus:border-indigo-500 focus:outline-none"
                  />
                  {faqs.length > 1 && (
                    <button
                      type="button"
                      onClick={() => handleRemoveFaq(idx)}
                      className="text-slate-500 hover:text-red-400 px-2"
                    >
                      ✕
                    </button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <div className="flex items-center justify-end gap-3 border-t border-slate-800 pt-4 mt-6">
            <button
              type="button"
              onClick={onClose}
              className="rounded-lg px-4 py-2 text-sm font-medium text-slate-300 hover:bg-slate-800 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={isLoading}
              className="rounded-lg bg-indigo-600 px-5 py-2 text-sm font-medium text-white hover:bg-indigo-500 disabled:opacity-50 transition-colors"
            >
              {isLoading ? "Saving KB..." : "Save & Inject Knowledge"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
