import * as TooltipPrimitive from '@radix-ui/react-tooltip';
import { cva, type VariantProps } from 'class-variance-authority';
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';
import { Info } from 'lucide-react';
import type { ButtonHTMLAttributes, ReactNode } from 'react';

export const cn=(...inputs:ClassValue[])=>twMerge(clsx(inputs));
const variants=cva('button',{variants:{variant:{default:'button-primary',outline:'button-outline',ghost:'button-ghost'}},defaultVariants:{variant:'default'}});
export function Button({className,variant,...props}:ButtonHTMLAttributes<HTMLButtonElement>&VariantProps<typeof variants>){return <button className={cn(variants({variant}),className)} {...props}/>;}
export function Tip({children}:{children:ReactNode}){return <TooltipPrimitive.Root><TooltipPrimitive.Trigger asChild><button className="info-button" aria-label="Explain this metric"><Info size={14}/></button></TooltipPrimitive.Trigger><TooltipPrimitive.Portal><TooltipPrimitive.Content className="tooltip" sideOffset={6}>{children}<TooltipPrimitive.Arrow className="tooltip-arrow"/></TooltipPrimitive.Content></TooltipPrimitive.Portal></TooltipPrimitive.Root>;}
export function Card({children,className}:{children:ReactNode;className?:string}){return <section className={cn('card',className)}>{children}</section>;}
