import React from 'react';
import { Check, X, ShieldCheck, Info } from 'lucide-react';

export const checkPasswordRules = (password = '') => {
  return {
    minLength: password.length >= 8,
    hasUpper: /[A-Z]/.test(password),
    hasLower: /[a-z]/.test(password),
    hasNumber: /[0-9]/.test(password),
    hasSpecial: /[@$!%*?&#^_\-\.+=\~]/.test(password),
  };
};

export const isPasswordValid = (password = '') => {
  const rules = checkPasswordRules(password);
  return rules.minLength && rules.hasUpper && rules.hasLower && rules.hasNumber && rules.hasSpecial;
};

const PasswordRulesGuide = ({ password = '', confirmPassword = null, isFocused = true }) => {
  const rules = checkPasswordRules(password);
  
  // Calculate score (0 to 5)
  const score = Object.values(rules).filter(Boolean).length;

  const getStrengthInfo = () => {
    if (!password) return { label: 'Empty', color: 'bg-slate-200', text: 'text-slate-400', width: '0%' };
    if (score <= 1) return { label: 'Very Weak', color: 'bg-red-500', text: 'text-red-600', width: '20%' };
    if (score === 2) return { label: 'Weak', color: 'bg-orange-500', text: 'text-orange-600', width: '40%' };
    if (score === 3) return { label: 'Fair', color: 'bg-amber-500', text: 'text-amber-600', width: '60%' };
    if (score === 4) return { label: 'Good', color: 'bg-blue-500', text: 'text-blue-600', width: '80%' };
    return { label: 'Strong', color: 'bg-emerald-500', text: 'text-emerald-600', width: '100%' };
  };

  const strength = getStrengthInfo();

  const ruleItems = [
    { key: 'minLength', label: 'At least 8 characters long', valid: rules.minLength },
    { key: 'hasUpper', label: 'At least one uppercase letter (A-Z)', valid: rules.hasUpper },
    { key: 'hasLower', label: 'At least one lowercase letter (a-z)', valid: rules.hasLower },
    { key: 'hasNumber', label: 'At least one number (0-9)', valid: rules.hasNumber },
    { key: 'hasSpecial', label: 'At least one special symbol (@$!%*?&#...)', valid: rules.hasSpecial },
  ];

  return (
    <div className="mt-2.5 p-3.5 bg-slate-50 rounded-xl border border-slate-200/80 text-xs transition-all">
      {/* Strength Bar */}
      <div className="mb-3">
        <div className="flex justify-between items-center mb-1 font-medium">
          <span className="text-slate-500 flex items-center gap-1">
            <ShieldCheck className="w-3.5 h-3.5 text-slate-400" />
            Password Strength:
          </span>
          <span className={`font-bold ${strength.text}`}>{strength.label}</span>
        </div>
        <div className="w-full bg-slate-200 h-1.5 rounded-full overflow-hidden">
          <div 
            className={`h-full ${strength.color} transition-all duration-300 rounded-full`}
            style={{ width: strength.width }}
          />
        </div>
      </div>

      {/* Rules Checklist */}
      <div className="space-y-1.5">
        <p className="font-semibold text-slate-600 mb-1 flex items-center gap-1">
          <Info className="w-3 h-3 text-slate-400" />
          Password Requirements:
        </p>
        {ruleItems.map((item) => (
          <div 
            key={item.key} 
            className={`flex items-center gap-1.5 transition-colors ${
              item.valid ? 'text-emerald-700 font-medium' : 'text-slate-400'
            }`}
          >
            <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center shrink-0 ${
              item.valid ? 'bg-emerald-100 text-emerald-700' : 'bg-slate-200 text-slate-400'
            }`}>
              {item.valid ? (
                <Check className="w-2.5 h-2.5 stroke-[3]" />
              ) : (
                <span className="w-1.5 h-1.5 rounded-full bg-slate-400" />
              )}
            </div>
            <span>{item.label}</span>
          </div>
        ))}

        {/* Confirmation check if confirmPassword provided */}
        {confirmPassword !== null && confirmPassword.length > 0 && (
          <div className={`flex items-center gap-1.5 pt-1 mt-1 border-t border-slate-200 ${
            password === confirmPassword ? 'text-emerald-700 font-medium' : 'text-red-600 font-medium'
          }`}>
            <div className={`w-3.5 h-3.5 rounded-full flex items-center justify-center shrink-0 ${
              password === confirmPassword ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-600'
            }`}>
              {password === confirmPassword ? (
                <Check className="w-2.5 h-2.5 stroke-[3]" />
              ) : (
                <X className="w-2.5 h-2.5 stroke-[3]" />
              )}
            </div>
            <span>{password === confirmPassword ? 'Passwords match' : 'Passwords do not match'}</span>
          </div>
        )}
      </div>
    </div>
  );
};

export default PasswordRulesGuide;
