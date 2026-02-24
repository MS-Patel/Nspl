
-- Create risk profile table to store questionnaire results
CREATE TABLE public.risk_profiles (
  id UUID NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID NOT NULL,
  risk_score INTEGER NOT NULL CHECK (risk_score >= 0 AND risk_score <= 100),
  risk_category TEXT NOT NULL,
  answers JSONB NOT NULL DEFAULT '{}',
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT now(),
  UNIQUE (user_id)
);

-- Enable RLS
ALTER TABLE public.risk_profiles ENABLE ROW LEVEL SECURITY;

-- RLS policies
CREATE POLICY "Users can view own risk profile"
ON public.risk_profiles FOR SELECT
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own risk profile"
ON public.risk_profiles FOR INSERT
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own risk profile"
ON public.risk_profiles FOR UPDATE
USING (auth.uid() = user_id);

-- Auto-update timestamp
CREATE TRIGGER update_risk_profiles_updated_at
BEFORE UPDATE ON public.risk_profiles
FOR EACH ROW
EXECUTE FUNCTION public.update_updated_at_column();
