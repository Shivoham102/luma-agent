"use client";

import { useState, FormEvent } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

interface FieldError {
  field: string;
  message: string;
}

export default function SignupPage() {
  const router = useRouter();
  const [formData, setFormData] = useState({
    name: "",
    email: "",
    password: "",
    linkedin_url: "",
    job_title: "",
    company: "",
    phone: "",
    twitter_x: "",
    luma_email: "",
    luma_password: "",
  });
  const [errors, setErrors] = useState<FieldError[]>([]);
  const [serverError, setServerError] = useState("");
  const [loading, setLoading] = useState(false);

  const EMAIL_RE = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

  function validate(): FieldError[] {
    const errs: FieldError[] = [];
    if (!formData.name.trim()) {
      errs.push({ field: "name", message: "Name is required" });
    }
    if (!formData.email.trim()) {
      errs.push({ field: "email", message: "Email is required" });
    } else if (!EMAIL_RE.test(formData.email.trim())) {
      errs.push({ field: "email", message: "Invalid email format" });
    }
    if (!formData.password) {
      errs.push({ field: "password", message: "Password is required" });
    } else if (formData.password.length < 8) {
      errs.push({
        field: "password",
        message: "Password must be at least 8 characters",
      });
    }
    return errs;
  }

  function fieldError(field: string): string | undefined {
    return errors.find((e) => e.field === field)?.message;
  }

  function handleChange(field: string, value: string) {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear field error on change
    setErrors((prev) => prev.filter((e) => e.field !== field));
    setServerError("");
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const validationErrors = validate();
    if (validationErrors.length > 0) {
      setErrors(validationErrors);
      return;
    }

    setLoading(true);
    setServerError("");
    try {
      const body: Record<string, string> = {
        name: formData.name.trim(),
        email: formData.email.trim(),
        password: formData.password,
      };
      // Include optional fields only if non-empty
      if (formData.linkedin_url.trim())
        body.linkedin_url = formData.linkedin_url.trim();
      if (formData.job_title.trim())
        body.job_title = formData.job_title.trim();
      if (formData.company.trim()) body.company = formData.company.trim();
      if (formData.phone.trim()) body.phone = formData.phone.trim();
      if (formData.twitter_x.trim())
        body.twitter_x = formData.twitter_x.trim();
      if (formData.luma_email.trim())
        body.luma_email = formData.luma_email.trim();
      if (formData.luma_password) body.luma_password = formData.luma_password;

      const res = await fetch(`${API_BASE}/auth/signup`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => null);
        const detail = data?.detail;
        if (typeof detail === "string") {
          setServerError(detail);
        } else if (Array.isArray(detail)) {
          // Pydantic validation errors
          setServerError(
            detail.map((d: { msg?: string }) => d.msg ?? "").join(", ")
          );
        } else {
          setServerError("Signup failed. Please try again.");
        }
        return;
      }

      router.push("/login");
    } catch {
      setServerError("Network error. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  const fields: {
    key: string;
    label: string;
    type: string;
    required: boolean;
    placeholder: string;
  }[] = [
    {
      key: "name",
      label: "Name",
      type: "text",
      required: true,
      placeholder: "Your full name",
    },
    {
      key: "email",
      label: "Email",
      type: "email",
      required: true,
      placeholder: "you@example.com",
    },
    {
      key: "password",
      label: "Password",
      type: "password",
      required: true,
      placeholder: "Minimum 8 characters",
    },
    {
      key: "linkedin_url",
      label: "LinkedIn URL",
      type: "url",
      required: false,
      placeholder: "https://linkedin.com/in/yourprofile",
    },
    {
      key: "job_title",
      label: "Job Title",
      type: "text",
      required: false,
      placeholder: "e.g. Software Engineer",
    },
    {
      key: "company",
      label: "Company",
      type: "text",
      required: false,
      placeholder: "e.g. Acme Corp",
    },
    {
      key: "phone",
      label: "Phone",
      type: "tel",
      required: false,
      placeholder: "+1 555 123 4567",
    },
    {
      key: "twitter_x",
      label: "Twitter/X Handle",
      type: "text",
      required: false,
      placeholder: "@yourhandle",
    },
    {
      key: "luma_email",
      label: "Luma Email",
      type: "email",
      required: false,
      placeholder: "Your Luma account email",
    },
    {
      key: "luma_password",
      label: "Luma Password",
      type: "password",
      required: false,
      placeholder: "Your Luma account password",
    },
  ];

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#0a0a0a] px-4 py-12">
      <div className="w-full max-w-md">
        <h1 className="mb-2 text-center text-2xl font-bold text-[#ededed]">
          Create an Account
        </h1>
        <p className="mb-6 text-center text-sm text-zinc-400">
          Sign up to discover and register for Luma events.
        </p>

        {serverError && (
          <div className="mb-4 rounded-lg border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-400">
            {serverError}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4" noValidate>
          {fields.map(({ key, label, type, required, placeholder }) => (
            <div key={key}>
              <label
                htmlFor={key}
                className="mb-1 block text-sm font-medium text-zinc-300"
              >
                {label}
                {required && <span className="ml-1 text-red-400">*</span>}
              </label>
              <input
                id={key}
                name={key}
                type={type}
                required={required}
                placeholder={placeholder}
                value={formData[key as keyof typeof formData]}
                onChange={(e) => handleChange(key, e.target.value)}
                className={`w-full rounded-lg border bg-zinc-800 px-4 py-2.5 text-sm text-zinc-100 placeholder:text-zinc-500 focus:outline-none ${
                  fieldError(key)
                    ? "border-red-500 focus:border-red-500"
                    : "border-zinc-600 focus:border-blue-500"
                }`}
              />
              {fieldError(key) && (
                <p className="mt-1 text-xs text-red-400">{fieldError(key)}</p>
              )}
            </div>
          ))}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-40"
          >
            {loading ? "Signing up..." : "Sign Up"}
          </button>
        </form>

        <p className="mt-6 text-center text-sm text-zinc-400">
          Already have an account?{" "}
          <Link href="/login" className="text-blue-400 hover:text-blue-300">
            Log in
          </Link>
        </p>
      </div>
    </div>
  );
}
